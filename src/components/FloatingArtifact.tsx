import React from 'react';

interface FloatingArtifactProps {
  children: React.ReactNode;
  className?: string;
}

export default function FloatingArtifact({ children, className = '' }: FloatingArtifactProps) {
  return (
    <div
      className={`bg-white rounded-[20px] p-5 border border-[#ececec]/80 shadow-[0_0_0_1px_rgba(4,23,43,0.05),0_20px_25px_-5px_rgba(0,0,0,0.08),0_8px_10px_-6px_rgba(0,0,0,0.04)] ${className}`}
    >
      {children}
    </div>
  );
}
