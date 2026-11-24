'use client';

import AvatarCursor from './AvatarCursor';

/** An illustrative pointer; the scroll scene drives its movement in CSS. */
export default function HeroDemoCursor({ paused }: { paused: boolean }) {
  return (
    <div className={`hero-demo-cursor-anchor ${paused ? 'is-manual' : ''}`} aria-hidden="true">
      <div className="hero-demo-cursor">
        <span className="hero-demo-cursor-click" />
        <AvatarCursor initials="AC" name="Alexa Chen (Admin)" color="green" pointerDirection="top-left" />
      </div>
    </div>
  );
}
