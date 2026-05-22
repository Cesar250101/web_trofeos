/** @odoo-module **/
/**
 * Web Trofeos — Quick Quote Calculator
 * Real-time price estimation based on product type, quantity, and engraving.
 */

const PRICES = {
    trofeo_resina:    { unit: 8900,  bulk50: 0.90, bulk100: 0.85 },
    trofeo_metal:     { unit: 14900, bulk50: 0.88, bulk100: 0.82 },
    medalla_zinc:     { unit: 3500,  bulk50: 0.90, bulk100: 0.85 },
    medalla_acrilico: { unit: 2900,  bulk50: 0.92, bulk100: 0.88 },
    placa_aluminio:   { unit: 6900,  bulk50: 0.90, bulk100: 0.85 },
    placa_madera:     { unit: 9900,  bulk50: 0.88, bulk100: 0.83 },
};

const ENGRAVING_UNIT = 1500; // CLP per unit

function formatCLP(value) {
    return "$ " + Math.round(value).toLocaleString("es-CL");
}

function calcTotal(product, qty, withEngraving) {
    const p = PRICES[product];
    if (!p) return { total: 0, discount: 0, pct: 0 };

    let pct = 1;
    if (qty >= 100) pct = p.bulk100;
    else if (qty >= 50) pct = p.bulk50;

    const engravingCost = withEngraving ? ENGRAVING_UNIT * qty : 0;
    const productCost   = p.unit * qty * pct;
    const total         = productCost + engravingCost;
    const discountPct   = Math.round((1 - pct) * 100);

    return { total, discountPct, pct };
}

const TrQuoteCalculator = {
    selector: ".s_tr_quote_calc",

    start(el) {
        const productSel  = el.querySelector(".tr-calc-product");
        const quantityEl  = el.querySelector(".tr-calc-quantity");
        const engravingEl = el.querySelector(".tr-calc-engraving");
        const outputEl    = el.querySelector(".tr-calc-output");
        const discountEl  = el.querySelector(".tr-calc-discount");

        if (!productSel || !quantityEl || !outputEl) return;

        function update() {
            const product     = productSel.value;
            const qty         = Math.max(1, parseInt(quantityEl.value, 10) || 1);
            const withEngrave = engravingEl ? engravingEl.checked : false;

            const { total, discountPct } = calcTotal(product, qty, withEngrave);

            outputEl.textContent = formatCLP(total);

            if (discountEl) {
                if (discountPct > 0) {
                    discountEl.textContent = `${discountPct}% descuento por volumen aplicado`;
                } else {
                    discountEl.textContent = "";
                }
            }
        }

        productSel.addEventListener("change", update);
        quantityEl.addEventListener("input", update);
        engravingEl?.addEventListener("change", update);

        update();
    },
};

export default TrQuoteCalculator;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(TrQuoteCalculator.selector).forEach((el) => {
        TrQuoteCalculator.start(el);
    });
});
