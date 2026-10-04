const headings = document.querySelectorAll("h1, h2, h3");

for (const heading of headings) {
    const text = heading.innerText;

    if (/\bM[1-5]\b/i.test(text)) {
        const product = heading.querySelector(".product-tile-headline");
        const hardware = heading.querySelector(".product-tile-subheading");
        if (!hardware) {
            console.log("No Hardware subheading found for:", text);
            continue;
        }

        const cleanedHardware = hardware?.innerText?.replace("chip", "").trim();
        const normalizedHardware = cleanedHardware.replace(/\s+or\s+/gi, ", ");
        const hardwareOptions = normalizedHardware
            .split(",")
            .map(item => item.trim())
            .filter(Boolean);

        console.log(hardwareOptions);
        console.log("RAW HARDWARE:", JSON.stringify(hardware?.innerText));
        console.log("CLEANED HARDWARE:", JSON.stringify(cleanedHardware));

        const productData = {
            product: product?.innerText?.trim() || "Unknown product",
            hardware: hardwareOptions
        };

        console.log(productData);
    }
}
