/** @odoo-module **/
/**
 * Web Trofeos — Hero Slider
 * Auto-advancing carousel with arrow and dot navigation.
 * Works on .s_tr_hero sections.
 */

import { registry } from "@web/core/registry";

const TrHeroSlider = {
    selector: ".s_tr_hero",

    start(el) {
        const slides = el.querySelectorAll(".tr-hero-slide");
        const dots   = el.querySelectorAll(".tr-hero-dot");
        const prev   = el.querySelector("[data-hero-prev]");
        const next   = el.querySelector("[data-hero-next]");

        if (!slides.length) return;

        let current  = 0;
        let timer    = null;
        const DELAY  = 5500; // ms

        // ── Helpers ──────────────────────────────────────────
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

        // ── Events ───────────────────────────────────────────
        prev?.addEventListener("click", () => { show(current - 1); startAuto(); });
        next?.addEventListener("click", () => { show(current + 1); startAuto(); });

        dots.forEach((dot, i) => {
            dot.addEventListener("click", () => { show(i); startAuto(); });
        });

        el.addEventListener("mouseenter", stopAuto);
        el.addEventListener("mouseleave", startAuto);

        // Touch / swipe support
        let touchStartX = 0;
        el.addEventListener("touchstart", (e) => { touchStartX = e.touches[0].clientX; }, { passive: true });
        el.addEventListener("touchend", (e) => {
            const dx = e.changedTouches[0].clientX - touchStartX;
            if (Math.abs(dx) > 50) {
                dx < 0 ? show(current + 1) : show(current - 1);
                startAuto();
            }
        }, { passive: true });

        // Pause when tab is hidden
        document.addEventListener("visibilitychange", () => {
            document.hidden ? stopAuto() : startAuto();
        });

        // ── Init ─────────────────────────────────────────────
        show(0);
        startAuto();
    },
};

// Register as a public widget (Odoo website frontend pattern)
export default TrHeroSlider;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(TrHeroSlider.selector).forEach((el) => {
        TrHeroSlider.start(el);
    });
});
