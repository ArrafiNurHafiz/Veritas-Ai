import React from 'react';

interface AvatarCursorProps {
  initials: string;
  name?: string;
  color?: 'green' | 'blue' | 'peach' | 'purple';
  pointerDirection?: 'bottom-right' | 'top-left';
  className?: string;
}

export default function AvatarCursor({
  initials,
  name,
  color = 'blue',
  pointerDirection = 'top-left',
  className = '',
}: AvatarCursorProps) {
  const colorMap = {
    green: {
      bg: 'bg-[#d8f3dc]',
      text: 'text-[#1b4332]',
      border: 'border-[#b7e4c7]',
      pointer: '#2d6a4f',
    },
    blue: {
      bg: 'bg-[#e0f2fe]',
      text: 'text-[#0369a1]',
      border: 'border-[#bae6fd]',
      pointer: '#0284c7',
    },
    peach: {
      bg: 'bg-[#fbe1d1]',
      text: 'text-[#5d2a1a]',
      border: 'border-[#f5cfb8]',
      pointer: '#5d2a1a',
    },
    purple: {
      bg: 'bg-[#ede9fe]',
      text: 'text-[#5b21b6]',
      border: 'border-[#ddd6fe]',
      pointer: '#6d28d9',
    },
  };

  const c = colorMap[color];

  return (
    <div className={`relative inline-flex items-center gap-2 group z-20 ${className}`}>
      {/* Pointer Cursor Arrow */}
      {pointerDirection === 'top-left' && (
        <svg
          className="absolute -top-3 -left-3 w-4 h-4 drop-shadow-sm pointer-events-none"
          viewBox="0 0 24 24"
          fill={c.pointer}
        >
          <path d="M3 3l7 18 3.5-7.5L21 10 3 3z" />
        </svg>
      )}

      {/* Circle Avatar */}
      <div
        className={`w-9 h-9 rounded-full ${c.bg} ${c.text} border ${c.border} flex items-center justify-center font-sans font-medium text-[12px] shadow-sm select-none transition-transform group-hover:scale-105`}
      >
        {initials}
      </div>

      {pointerDirection === 'bottom-right' && (
        <svg
          className="absolute -bottom-2 -right-2 w-4 h-4 drop-shadow-sm pointer-events-none"
          viewBox="0 0 24 24"
          fill={c.pointer}
        >
          <path d="M3 3l7 18 3.5-7.5L21 10 3 3z" />
        </svg>
      )}

      {/* Name Label */}
      {name && (
        <span className="text-[12px] font-sans font-medium text-[#17191c] bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full border border-[#ececec] shadow-sm whitespace-nowrap">
          {name}
        </span>
      )}
    </div>
  );
}
