const statusHeading = document.querySelector(".status h2")
const statusText = document.querySelector(".status p");
const statusSection = document.querySelector(".status");
const modelPicker = document.getElementById("model-picker");
const modelSelect = document.getElementById("model-select")
const benchmarkSection = document.createElement("div");

benchmarkSection.id = "benchmark-results";
benchmarkSection.className = "truthlens-benchmark-results";

benchmarkSection.setAttribute("aria-live", "polite");
statusSection?.appendChild(benchmarkSection);

let detectedModels = [];
let benchmarkDatabasePromise = null;
let BenchmarkRequest = 0;

function formatSpecifications(specifications) {
    return Object.entries(specifications)
        .filter(([key]) => key != "model")
        .map(([key, value]) => {
            const label = key.replaceAll("_", " ");

            if (key === "clock_rate" && typeof value === "number") {
                return `clock_rate: ${value} GHz`;
            }

            if (key === "clock_rate" && value && typeof value === "object") {
                const rates = Object.entries(value)
                    .map(([kind, ghz]) => `${kind} ${ghz} GHz`)
                    .join(", ");

                return `clock_rate: ${rates}`;
            }

            if (key === "vram") {
                return `VRAM: ${value} GB`;
            }

            return `${label}: ${value}`;
        })
        .join(" • ");
}

async function loadBenchmarkDatabase() {
    if (!benchmarkDatabasePromise) {
        benchmarkDatabasePromise = (async () => {
            const url = chrome.runtime.getURL("database/benchmarks.json");
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Could not load ${url}: HTTP ${response.status}`);
            }

            return response.json();
        })();
    }

    try {
        return await benchmarkDatabasePromise;
    }
    catch (error) {
        benchmarkDatabasePromise = null;
        throw error;
    }
}

function findBenchmarksRecord(match, benchmarkModels) {
    const modelName = match.name ?? "";
    const possibleNames = [modelName];

    if (/^NVIDIA GeForce /i.test(modelName)) {
        possibleNames.push(modelName.replace(/^NVIDIA GeForce /i, "NVIDIA "));
    }

    else if (/^NVIDIA RTX /i.test(modelName)) {
        possibleNames.push(modelName.replace(/^NVIDIA /i, "NVIDIA GeForce "));
    }

    for (const name of possibleNames) {
        if (benchmarkModels[name]) {
            return benchmarkModels[name];
        }
    }

    return null;
}

function formatScore(score) {
    return new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0
    }).format(score);
}

function createBenchmarkCard(match, comparison) {
    const card = document.createElement("div");
    card.className = "truthlens-benchmark";

    const heading = document.createElement("h3");
    heading.textContent = `${match.name} vs ${comparison.previousGeneration}`;
    card.appendChild(heading);

    const benchmarkName = document.createElement("p");
    benchmarkName.textContent = comparison.benchmarkName;
    card.appendChild(benchmarkName);

    for (const metric of comparison.metrics) {
        const change = ((metric.currentScore - metric.previousScore) / metric.previousScore) * 100;
        const sign = change > 0 ? "+" : "";
        const metricLine = document.createElement("p");
        metricLine.textContent =
            `${metric.label}: ${formatScore(metric.currentScore)} vs ` +
            `${formatScore(metric.previousScore)} (${sign}${change.toFixed(1)}%)`;
        card.appendChild(metricLine);
    }

    if (comparison.note) {
        const note = document.createElement("p");
        note.textContent = comparison.note;
        card.appendChild(note);
    }

    const sourceLink = document.createElement("a");
    sourceLink.href = comparison.source.url;
    sourceLink.target = "_blank";
    sourceLink.rel = "noopener noreferrer";
    sourceLink.textContent = `${comparison.source.name} results ↗`;
    card.appendChild(sourceLink);

    return card;
}

async function showBenchmarkComparison(match) {
    const request = ++BenchmarkRequest;
    benchmarkSection.replaceChildren();
    benchmarkSection.setAttribute("aria-busy", "true");
    const loading = document.createElement("p");
    loading.textContent = "Loading benchmarks...";
    benchmarkSection.appendChild(loading);

    try {
        const benchmarkDatabase = await loadBenchmarkDatabase();

        if (request !== BenchmarkRequest) {
            return;
        }

        benchmarkSection.replaceChildren();
        const comparison = findBenchmarksRecord(match, benchmarkDatabase.models ?? {});

        if (!comparison) {
            const message = document.createElement("p");
            message.textContent = `No benchmark comparison data available for ${match.name} yet.`;
            benchmarkSection.appendChild(message);
            return;
        }

        benchmarkSection.appendChild(createBenchmarkCard(match, comparison));
    }

    catch (error) {
        if (request !== BenchmarkRequest) {
            return;
        }
        console.error("[TruthLens benchmarks]", error);
        benchmarkSection.replaceChildren();
        const message = document.createElement("p");
        message.textContent = "Benchmark data could not be loaded.";
        benchmarkSection.appendChild(message);
    }

    finally {
        if (request === BenchmarkRequest) {
            benchmarkSection.setAttribute("aria-busy", "false");
        }
    }
}

async function showSelectedHardware() {
    const match = detectedModels[Number(modelSelect.value)];
    if (!match) {
        return;
    }

    const specs = formatSpecifications(match.specifications);
    statusText.textContent = `${match.name}\n${specs}`;
    await showBenchmarkComparison(match);
}

modelSelect.addEventListener("change", showSelectedHardware);

async function showPageScan() {
    try {
        const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true
        });

        if (!tab?.id) {
            throw new Error("Could not find the active tab.");
        }

        await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ["content/content.js"]
        });

        const scan = await chrome.tabs.sendMessage(tab.id, {
            type: "TRUTHLENS_GET_SCAN"
        });

        if (!scan) {
            throw new Error (
                "The page script returned no scan data. Check that the updated content/content.js is loaded."
            );
        }

        if (scan.status === "error") {
            throw new Error(scan.error);
        }

        if (scan.matches.length === 0) {
            statusHeading.textContent = "No database match";
            statusText.textContent = 
                `Scanned "${scan.page.title}", but found no hardware model` + 
                "from the current database.";
            return;
        }

        statusHeading.textContent =
            `Detected ${scan.matches.length} hardware model` +
            (scan.matches.length === 1 ? "" : "s");

        detectedModels = scan.matches;
        modelSelect.replaceChildren();
        detectedModels.forEach((match, index) => {
            const option = document.createElement("option");
            option.value = String(index);
            option.textContent = match.name;
            modelSelect.appendChild(option);
        });
        modelSelect.value = "0";
        modelPicker.hidden = detectedModels.length < 2;
        
        await showSelectedHardware();
    }

    catch (error) {
        console.error("[TruthLens popup]", error);
        statusHeading.textContent = "Scan error";
        statusText.textContent = error?.message ?? String(error);
    }
}
showPageScan();
