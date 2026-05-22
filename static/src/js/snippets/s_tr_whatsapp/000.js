/** @odoo-module **/
/**
 * Web Trofeos — WhatsApp Floating Button
 * Builds the href from the company phone stored in data-phone,
 * prepending the default whatsapp.com/send URL.
 */

const TrWhatsApp = {
    selector: ".s_tr_whatsapp",

    start(el) {
        const link = el.querySelector(".tr-whatsapp-link");
        if (!link) return;

        // Read phone from data attribute set by QWeb
        const rawPhone = el.dataset.phone || "";
        const phone = rawPhone.replace(/[\s\-().+]/g, "");

        const defaultMessage = encodeURIComponent(
            "Hola, me gustaría cotizar algunos trofeos/medallas. ¿Pueden ayudarme?"
        );

        if (phone) {
            link.href = `https://wa.me/${phone}?text=${defaultMessage}`;
        } else {
            // Fallback: open whatsapp.com without phone
            link.href = `https://wa.me/?text=${defaultMessage}`;
        }

        // Scroll-triggered visibility: show after 300px
        const showThreshold = 300;
        el.style.opacity = "0";
        el.style.transform = "translateY(16px)";
        el.style.transition = "opacity 0.3s ease, transform 0.3s ease";

        function onScroll() {
            if (window.scrollY > showThreshold) {
                el.style.opacity = "1";
                el.style.transform = "translateY(0)";
            } else {
                el.style.opacity = "0";
                el.style.transform = "translateY(16px)";
            }
        }

        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll(); // Check on load
    },
};

export default TrWhatsApp;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(TrWhatsApp.selector).forEach((el) => {
        TrWhatsApp.start(el);
    });
});
