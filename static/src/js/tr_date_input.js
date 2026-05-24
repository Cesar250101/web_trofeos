/** @odoo-module **/
/**
 * Web Trofeos — Date input auto-formatter
 * Forces dd/mm/aaaa formatting on .tr-date-input fields regardless of browser locale.
 * Inserts slashes as the user types and rejects non-digit characters.
 */

function formatDateInput(input) {
    function onInput() {
        const raw = input.value.replace(/\D/g, "").slice(0, 8);
        let formatted = raw;
        if (raw.length > 4) {
            formatted = `${raw.slice(0, 2)}/${raw.slice(2, 4)}/${raw.slice(4)}`;
        } else if (raw.length > 2) {
            formatted = `${raw.slice(0, 2)}/${raw.slice(2)}`;
        }
        input.value = formatted;
    }

    function onBlur() {
        const v = input.value;
        if (!v) return;
        const m = v.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
        if (!m) {
            input.setCustomValidity("Formato inválido. Usa dd/mm/aaaa");
            return;
        }
        const dd = parseInt(m[1], 10);
        const mm = parseInt(m[2], 10);
        let yyyy = parseInt(m[3], 10);
        if (yyyy < 100) yyyy += 2000;
        if (dd < 1 || dd > 31 || mm < 1 || mm > 12) {
            input.setCustomValidity("Fecha inválida");
            return;
        }
        input.setCustomValidity("");
        const pad = (n) => String(n).padStart(2, "0");
        input.value = `${pad(dd)}/${pad(mm)}/${yyyy}`;
    }

    input.addEventListener("input", onInput);
    input.addEventListener("blur", onBlur);
    input.addEventListener("focus", () => input.setCustomValidity(""));
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tr-date-input").forEach(formatDateInput);
});
