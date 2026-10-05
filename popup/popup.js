const statusHeading = document.querySelector(".status h2")
const statusText = document.querySelector(".status p");

function formatSpecifications(specifications) {
    return Object.entries(specifications)
        .filter(([key]) => key != "model")
        .map(([key, value]) => {
            const label = key.replaceAll("_", " ");

            if (key === "clock_rate" && typeof value === "number") {
                return `clock_rate: ${value} GHz`;
            }

            if (key === "clock_rate" && value && typeof value === "number") {
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

async function showPageScan() {
    try {
        const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true
        });

        if (!tab?.id) {
            throw new Error("Could not find the active tab.");
        }

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

        statusText.textContent = scan.matches
            .map(match => {
                const specs = formatSpecifications(match.specifications);
                return `${match.name}\n${specs}`;
            })
            .join("\n\n");
    }

    catch (error) {
        console.error("[TruthLens popup]", error);
        statusHeading.textContent = "Scan error";
        statusText.textContent = error?.message ?? String(error);
    }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "TRUTHLENS_GET_SCAN") {
        return false;
    }

    scanPromise.then (
        sendResponse,
        error => sendResponse ({
            status: "error",
            error: error.message
        })
    );

    return true;
})

showPageScan();
