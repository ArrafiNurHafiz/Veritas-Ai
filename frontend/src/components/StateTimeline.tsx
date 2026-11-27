import React from 'react';
import { ExecutionEvent, ExecutionStatus } from '@/lib/types';

interface StateTimelineProps {
  events: ExecutionEvent[];
  currentStatus: ExecutionStatus;
}

export default function StateTimeline({ events, currentStatus }: StateTimelineProps) {
  const getStageColor = (stage: ExecutionStatus) => {
    switch (stage) {
      case 'SUCCEEDED':
        return 'bg-emerald-500 text-white';
      case 'WAITING_APPROVAL':
      case 'APPROVAL_REQUIRED':
        return 'bg-amber-500 text-white';
      case 'DENIED':
      case 'REJECTED':
      case 'FAILED':
        return 'bg-rose-500 text-white';
      default:
        return 'bg-[#192319] text-white';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-[14px] font-medium text-[#192319]">State Machine Timeline</h4>
        <span className="text-[12px] font-mono text-[#2D372D]">
          Current: <strong className="text-[#192319]">{currentStatus}</strong>
        </span>
      </div>

      <div className="relative border-l-2 border-[#DCDCD7] ml-3.5 space-y-6 py-2">
        {events.map((evt, idx) => (
          <div key={evt.id || idx} className="relative pl-6 group">
            {/* Step dot */}
            <div
              className={`absolute -left-[17px] top-0.5 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${getStageColor(
                evt.stage
              )} ring-4 ring-white`}
            >
              {evt.sequence}
            </div>

            {/* Event Content */}
            <div className="bg-[#F8F8F8] p-3.5 rounded-xl border border-[#DCDCD7] space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-[#192319]">{evt.stage}</span>
                <span className="text-[11px] text-[#6D7344] font-mono">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-[13px] text-[#2D372D] leading-snug">{evt.message}</p>
              {evt.digest && (
                <div className="pt-1 text-[11px] font-mono text-[#6D7344] truncate">
                  Digest: {evt.digest}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
