const headings = document.querySelectorAll("h1, h2, h3");

for (const heading of headings) {
    const text = heading.innerText;

    if (text.includes("M5")) {
        const product = heading.querySelector(".product-tile-headline");
        const hardware = heading.querySelector(".product-tile-subheading");

        const cleanedHardware = hardware?.innerText?.replace("chip", "").trim();

        console.log("RAW HARDWARE:", JSON.stringify(hardware?.innerText));
        console.log("CLEANED HARDWARE:", JSON.stringify(cleanedHardware));

        const productData = {
            product: product?.innerText,
            hardware: cleanedHardware
        };

        console.log(productData);
    }
}
