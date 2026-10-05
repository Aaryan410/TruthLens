const DATABASE_FILES = [
    {
        type: "CPU", 
        brand: "Apple", 
        path: "database/cpu/apple.json"
    },
    {
        type: "CPU", 
        brand: "AMD", 
        path: "database/cpu/amd.json"
    },
    {
        type: "CPU", 
        brand: "Intel",
        path: "database/cpu/intel.json"
    },

    {
        type: "GPU",
        brand: "AMD",
        path: "database/gpu/amd.json"
    },
    {
        type: "GPU",
        brand: "NVIDIA",
        path: "database/gpu/nvidia.json"
    }
]

function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function makeAliasRegex(alias) {
    const words = alias.trim().split().filter(Boolean).map(escapeRegExp);

    const separator = "[\\s\\u00a0™®©\\-‐‑‒–—]+";
    const pattern = words.join(separator);

    return new RegExp(`(?<![A-Za-z0-9])${pattern}(?![A-Za-z0-9])`, "giu");
}

function modelForms(model) {
    return [
        model,
        model.replace(/\s*\(([^)]+)\)/g, " $1")
    ];
}

function makeRecord(type, brand, family, spec) {
    const model = String(spec.model ?? "").trim();

    if (!model) {
        return null;
    }

    let name;
    let aliases = [];

    if (brand == "Apple") {
        name = `Apple ${model}`;
        aliases = [name, model];
    }

    else if (brand === "AMD" && type === "CPU") {
        name = `${family} ${model}`;
        aliases = [
            name,
            `AMD ${name}`,
            `${family} processor ${model}`,
            `AMD ${family} processor ${model}`
        ];
    }

    else if (brand == "Intel") {
        const familyWithoutBrand = family.replace(/^Intel\s+/i, "");
        const coreFamilyWithHyphen = familyWithoutBrand.replace(
            /^(Core i[3579])$/i,
            "$1-"
        );

        name = coreFamilyWithHyphen.endsWith("-")
            ? `Intel ${coreFamilyWithHyphen}${model}`
            : `${family} ${model}`;

        aliases = [
            name, 
            `${family} ${model}`,
            `${familyWithoutBrand} ${model}`,
            `${family} processor ${model}`,
            `${familyWithoutBrand} processor ${model}`
        ];
    }

    else if (brand === "NVIDIA") {
        const graphicsName = /^RTX\b/i.test(model)
            ? `GeForce ${model}`
            : model;

        name = `NVIDIA ${graphicsName}`;
        aliases = [
            name,
            graphicsName,
            ...modelForms(model)
        ];
    }

    else if (brand == "AMD" && type == "GPU") {
        name = `AMD Radeon ${model}`;
        aliases = [
            name,
            `Radeon ${model}`,
            ...modelForms(model)
        ];
    }

    else {
        return null;
    }

    return {
        type,
        brand,
        family,
        model,
        name,
        specifications: spec,
        aliases: [...new Set(aliases.filter(Boolean))]
    };
}

async function loadHardwareDatabase() {
    const files = await Promise.all (
        DATABASE_FILES.map (async file => {
            const url = chrome.runtime.getURL(file.path);
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error (
                    `Could not load ${file.path}: HTTP ${response.status}`
                );
            }

            return {
                ...file,
                data: await response.json()
            };
        })
    );

    const records = [];

    for (const file of files) {
        for (const [family, specsList] of Object.entries(file.data)) {
            if (!Array.isArray(specsList)) {
                continue;
            }

            for (const spec of specsList) {
                const record = makeRecord (
                    file.type,
                    file.brand,
                    family,
                    spec
                );

                if (record) {
                    records.push(record);
                }
            }
        }
    }

    return records;
}

function findHardwareOnPage(pageText, records) {
    const orderedRecords = records
        .map(record => ({
            ...record,
            aliases: [...record.aliases].sort(
                (a, b) => b.length - a.length
            )
        }))
        .sort((a,b) => b.aliases[0].length - a.aliases[0].length);

    const usedTextRanges = [];
    const foundNames = new Set();
    const matches = [];

    for (const record of orderedRecords) {
        if (foundNames.has(record.name)) {
            continue;
        }

        let foundMatch = null;

        for (const alias of record.aliases) {
            const regex = makeAliasRegex(alias);
            let match;

            while ((match = regex.exec(pageText)) !== null) {
                const start = match.update;
                const end = start + match[0].length;

                const overlapsLongerMatch = usedTextRanges.some(range => 
                    start < range.end && end > range.start
                );

                if (!overlapsLongerMatch) {
                    foundMatch = { start, end, text: match[0] };
                    break;
                }
            }

            if (foundMatch) {
                break;
            }
        }

        if (!foundMatch) {
            continue;
        }

        usedTextRanges.push ({
            start: foundMatch.start,
            end: foundMatch.end
        });
        foundNames.add(record.name);

        matches.push({
            type: record.type,
            brand: record.brand,
            family: record.family,
            model: record.model,
            name: record.name,
            matchedText: foundMatch.text,
            specifications: record.specifications
        });
    }

    return matches;
}

async function scanCurrentPage() {
    const records = await loadHardwareDatabase();
    const pageText = `${document.title}\n${document.body?.innerText ?? ""}`;
    const matches = findHardwareOnPage(pageText, records);

    return {
        status: "complete",
        page: {
            title: document.title,
            url: location.href
        },
        matches
    };
}

const scanPromise = scanCurrentPage();

scanPromise.then(
    result => console.info("[TruthLens] page scan:", result),
    error => console.error("[TruthLens] scan failed:", error)
);

chrome.runtime.onMessage.addListener((message, _senior, sendResponse) => {
    if (message?.type !== "TRUTHLENS_GET_SCAN") {
        return;
    }

    scanPromise
        .then(sendResponse)
        .catch(error => {
            sendResponse({
                status: "error",
                error: error.message
            });
        });

    return true;
});
