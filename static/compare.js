const form = document.getElementById("compare-form");

form.addEventListener("change", (event) => {
    const changed = event.target;

    if (changed.tagName !== "SELECT") {
        return;
    }

    if (changed.name === "hardware") {
        const dropdowns = form.querySelectorAll("[data-side] select");

        dropdowns.forEach(dropdown => {
            dropdown.disabled = true;
        });
    } 
    else {
        const card = changed.closest("[data-side]");

        if (!card) {
            return;
        }

        const dropdowns = [...card.querySelectorAll("select")];
        const changedIndex = dropdowns.indexOf(changed);

        dropdowns.slice(changedIndex + 1).forEach(dropdown => {
            dropdown.disabled = true;
        });
    }

    form.requestSubmit();
});