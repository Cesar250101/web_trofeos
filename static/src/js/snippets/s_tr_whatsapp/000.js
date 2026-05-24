/** @odoo-module **/
/**
 * Web Trofeos — WhatsApp Floating Button
 * Builds the href from the company phone stored in data-phone,
 * prepending the default wa.me URL.
 */

const TrWhatsApp = {
    selector: ".s_tr_whatsapp",

    start(el) {
        const link = el.querySelector(".tr-whatsapp-link");
        if (!link) return;

        const rawPhone = el.dataset.phone || "";
        const phone = rawPhone.replace(/[\s\-().+]/g, "");

        const defaultMessage = encodeURIComponent(
            "Hola, me gustaría cotizar trofeos."
        );

        link.href = phone
            ? `https://wa.me/${phone}?text=${defaultMessage}`
            : `https://wa.me/?text=${defaultMessage}`;
    },
};

export default TrWhatsApp;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(TrWhatsApp.selector).forEach((el) => {
        TrWhatsApp.start(el);
    });
});
