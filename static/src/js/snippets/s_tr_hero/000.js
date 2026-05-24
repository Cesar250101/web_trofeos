/** @odoo-module **/
/**
 * Web Trofeos — Hero
 * The new heraldic hero is a static showcase (rings + featured SVG).
 * Slider behavior is retained for backwards-compat if a snippet still uses
 * .tr-hero-slide markup; otherwise the file is a no-op.
 */

const TrHero = {
    selector: ".s_tr_hero",

    start(el) {
        const slides = el.querySelectorAll(".tr-hero-slide");
        if (!slides.length) return;

        const dots = el.querySelectorAll(".tr-hero-dot");
        const prev = el.querySelector("[data-hero-prev]");
        const next = el.querySelector("[data-hero-next]");

        let current = 0;
        let timer = null;
        const DELAY = 5500;

        function show(idx) {
            slides[current].classList.remove("is-active");
            dots[current]?.classList.remove("is-active");
            current = (idx + slides.length) % slides.length;
            slides[current].classList.add("is-active");
            dots[current]?.classList.add("is-active");
        }

        function startAuto() {
            clearInterval(timer);
            timer = setInterval(() => show(current + 1), DELAY);
        }

        function stopAuto() {
            clearInterval(timer);
        }

        prev?.addEventListener("click", () => { show(current - 1); startAuto(); });
        next?.addEventListener("click", () => { show(current + 1); startAuto(); });
        dots.forEach((dot, i) => dot.addEventListener("click", () => { show(i); startAuto(); }));

        el.addEventListener("mouseenter", stopAuto);
        el.addEventListener("mouseleave", startAuto);

        show(0);
        startAuto();
    },
};

export default TrHero;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(TrHero.selector).forEach((el) => TrHero.start(el));
});
