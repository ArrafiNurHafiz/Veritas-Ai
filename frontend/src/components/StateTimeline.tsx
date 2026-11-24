import React from 'react';
import { ExecutionEvent, ExecutionStatus } from '@/lib/types';
import { CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react';

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
        return 'bg-[#17191c] text-white';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-[14px] font-medium text-[#17191c]">State Machine Timeline</h4>
        <span className="text-[12px] font-mono text-[#777b86]">
          Current: <strong className="text-[#17191c]">{currentStatus}</strong>
        </span>
      </div>

      <div className="relative border-l-2 border-[#ececec] ml-3.5 space-y-6 py-2">
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
            <div className="bg-[#fafafb] p-3.5 rounded-xl border border-[#ececec] space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-[#17191c]">{evt.stage}</span>
                <span className="text-[11px] text-[#979799] font-mono">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-[13px] text-[#777b86] leading-snug">{evt.message}</p>
              {evt.digest && (
                <div className="pt-1 text-[11px] font-mono text-[#979799] truncate">
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
