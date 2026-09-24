const headings = document.querySelectorAll("h1, h2, h3");

for (const heading of headings) {
    const text = heading.innerText;

    if (text.includes("M5")) {
        const hardware = heading.querySelector(".product-tile-subheading");

        console.log("Product:", heading.querySelector(".product-tile-headline")?.innerText);
        console.log("Hardware:", hardware?.innerText);
    }
}
