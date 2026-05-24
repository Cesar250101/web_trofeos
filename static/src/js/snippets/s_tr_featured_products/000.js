/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Sincroniza los puntos indicadores custom (.tr-npc-dots) con el estado
 * del carrusel Bootstrap, escuchando el evento 'slid.bs.carousel'.
 * Bootstrap maneja el avance; este widget solo actualiza la clase activa.
 */
publicWidget.registry.TrNewProductsCarousel = publicWidget.Widget.extend({
    selector: "#trNewProductsCarousel",

    start() {
        this._onSlid = this._onSlid.bind(this);
        this.el.addEventListener("slid.bs.carousel", this._onSlid);
        return this._super(...arguments);
    },

    destroy() {
        this.el.removeEventListener("slid.bs.carousel", this._onSlid);
        this._super(...arguments);
    },

    _onSlid(event) {
        const dots = this.el.querySelectorAll(".tr-npc-dots button");
        dots.forEach((dot, i) => {
            dot.classList.toggle("active", i === event.to);
        });
    },
});
