const form = document.getElementById("compare-form");

form.addEventListener("change", (event) => {
    const changed = event.target;

    if (changed.tagName !== "SELECT") {
        return;
    }

    if (changed.name === "hardware") {
        form.querySelectorAll("[data-side] select").forEach(select => {
            select.disabled = true;
        });
    } 
    else {
        const card = changed.closest("[data-side]");

        if (!card) {
            return;
        }

        const selects = [...card.querySelectorAll("select")];
        const index = selects.indexOf(changed);

        selects.slice(index + 1).forEach(select => {
            select.disabled = true;
        });
    }

    form.requestSubmit();
});