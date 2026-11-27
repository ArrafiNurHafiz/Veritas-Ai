'use client';

import React, { useEffect, useRef } from 'react';

const PALETTE = ['#ABE082', '#F1BE23', '#043423', '#BED1E4', '#192319'];

export default function SauceHeroCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let rafId = 0;
    let scrollProgress = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const onScroll = () => {
      scrollProgress = Math.min(1, window.scrollY / Math.max(1, window.innerHeight));
    };

    resize();
    onScroll();
    window.addEventListener('resize', resize);
    window.addEventListener('scroll', onScroll, { passive: true });

    let t = 0;
    const draw = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      const cell = 28;
      const cols = Math.ceil(w / cell) + 1;
      const rows = Math.ceil(h / cell) + 1;

      // Flowing kinetic pixel wave + subtle telemetry arcs (Sauce Labs hero canvas vibe)
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const nx = c / Math.max(1, cols);
          const ny = r / Math.max(1, rows);
          // Keep center-top clear for editorial serif typography readability
          const distCenter = Math.hypot((nx - 0.5) * 1.4, (ny - 0.42) * 1.6);
          if (distCenter < 0.36) continue;

          const wave =
            Math.sin(c * 0.32 + t * 1.35 + scrollProgress * 4.5) *
            Math.cos(r * 0.38 - t * 0.9 + scrollProgress * 2.5);

          if (wave > 0.62) {
            const colorIdx = (c * 3 + r * 7) % PALETTE.length;
            const alpha = Math.min(0.42, (wave - 0.62) * 1.15) * Math.min(1, (distCenter - 0.36) * 2.4);
            ctx.fillStyle = PALETTE[colorIdx];
            ctx.globalAlpha = alpha;
            ctx.fillRect(c * cell + 3, r * cell + 3, cell - 6, cell - 6);
          }
        }
      }

      // Subtle kinetic ribbon lines across lower hero
      ctx.globalAlpha = 0.16;
      ctx.strokeStyle = '#043423';
      ctx.lineWidth = 1.25;
      for (let band = 0; band < 3; band++) {
        ctx.beginPath();
        const baseY = h * (0.76 + band * 0.06);
        for (let x = 0; x <= w; x += 24) {
          const y =
            baseY +
            Math.sin(x * 0.008 + t * (0.9 + band * 0.25) + scrollProgress * 3) * (14 + band * 5);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;

      if (!prefersReduced) {
        t += 0.016;
        rafId = requestAnimationFrame(draw);
      }
    };

    draw();

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('resize', resize);
      window.removeEventListener('scroll', onScroll);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 w-full h-full"
    />
  );
}
