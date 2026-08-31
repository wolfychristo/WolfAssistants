import React, { useCallback, useEffect, useRef, useState } from 'react';
import { wolfyAPI } from '../services/api';

type Msg = { id: string; role: 'user' | 'wolfy'; text?: string; intent?: string; status?: string; context?: any; result?: any; ask?: string };

type WolfyChatProps = { mode?: 'floating' | 'page' };

const WolfyChat: React.FC<WolfyChatProps> = ({ mode = 'floating' }) => {
  const [open, setOpen] = useState(mode === 'page');
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [pendingContext, setPendingContext] = useState<any | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, open]);

  const send = useCallback(async (message: string, context?: any) => {
    if (!message.trim()) return;
    const userMsg: Msg = { id: crypto.randomUUID(), role: 'user', text: message };
    setMessages((m) => [...m, userMsg]);
    setSending(true);
    try {
      // Use the new session-based API format
      const res = await wolfyAPI.chat({
        message,
        // For backward compatibility, we'll create a new session for each message
        // In a real implementation, you might want to maintain session state
      });
      const d = res?.data || {};
      const wolfyMsg: Msg = {
        id: crypto.randomUUID(),
        role: 'wolfy',
        text: d.message?.content || d.message?.message || 'No response',
        intent: d.message?.intent,
        status: d.message?.status,
        context: d.message?.message_metadata,
        result: d.message?.message_metadata,
        ask: d.message?.status === 'confirm' ? 'Please confirm details' : undefined,
      };
      setMessages((m) => [...m, wolfyMsg]);
      if (d.message?.status === 'confirm') {
        setPendingContext(d.message?.message_metadata || {});
      } else {
        setPendingContext(null);
      }
    } catch (e: any) {
      setMessages((m) => [...m, { id: crypto.randomUUID(), role: 'wolfy', text: e?.message || 'Error' }]);
    } finally {
      setSending(false);
    }
  }, [messages]);

  const onConfirm = useCallback(() => {
    if (!messages.length) return;
    const last = messages[messages.length - 1];
    if (last.role === 'wolfy' && last.status === 'confirm') {
      const ctx = { ...(last.context || {}) };
      const actionPhrase = last.intent === 'send_email'
        ? `Send email to ${ctx.to}`
        : last.intent === 'schedule_meeting'
        ? `Schedule meeting`
        : `Proceed`;
      send(actionPhrase, ctx);
    }
  }, [messages, send]);

  const onEditContext = useCallback((patch: any) => {
    setPendingContext((c: any) => ({ ...(c || {}), ...(patch || {}) }));
  }, []);

  const onSend = useCallback(() => {
    const ctx = pendingContext || undefined;
    send(input, ctx);
    setInput('');
  }, [input, send, pendingContext]);

  const containerClass = mode === 'floating' ? 'fixed bottom-5 right-5 z-50' : 'max-w-3xl mx-auto w-full pt-20 px-4';
  const panelClass = mode === 'floating' ? 'w-96 max-w-[95vw] h-[28rem]' : 'w-full h-[calc(100vh-8rem)]';

  return (
    <div className={containerClass}>
      {mode === 'floating' && !open ? (
        <button onClick={() => setOpen(true)} className="px-4 py-2 rounded-full shadow bg-blue-600 text-white">Chat with Wolfy</button>
      ) : (
        <div className={`${panelClass} bg-white shadow-xl rounded-lg flex flex-col`}>
          <div className="px-3 py-2 border-b flex items-center justify-between">
            <div className="font-semibold">Wolfy</div>
            {mode === 'floating' ? (
              <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-gray-700">✕</button>
            ) : <div />}
          </div>
          <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-2">
            {messages.map((m) => (
              <div key={m.id} className={m.role === 'user' ? 'text-right' : 'text-left'}>
                <div className={`inline-block max-w-[85%] break-words px-3 py-2 rounded-lg ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'}`}>
                  <div className="whitespace-pre-wrap text-sm break-words">{m.text || m.ask || ''}</div>
                  {m.status === 'confirm' && m.context ? (
                    <div className="mt-2 text-xs text-gray-700">
                      {m.intent === 'send_email' ? (
                        <div className="space-y-1">
                          <div>To: <input className="border rounded px-1" value={pendingContext?.to ?? m.context.to ?? ''} onChange={(e)=>onEditContext({ to: e.target.value })} /></div>
                          <div>Subject: <input className="border rounded px-1 w-56" value={pendingContext?.subject ?? m.context.subject ?? ''} onChange={(e)=>onEditContext({ subject: e.target.value })} /></div>
                          <div>Body:</div>
                          <textarea className="border rounded p-1 w-64 h-20" value={pendingContext?.body ?? m.context.body ?? ''} onChange={(e)=>onEditContext({ body: e.target.value })} />
                          <div className="pt-1 flex gap-2 justify-end">
                            <button onClick={onConfirm} className="px-3 py-1 bg-blue-600 text-white rounded">Confirm & Send</button>
                          </div>
                        </div>
                      ) : m.intent === 'schedule_meeting' ? (
                        <div className="space-y-1">
                          <div>Title: <input className="border rounded px-1 w-56" value={pendingContext?.title ?? m.context.title ?? ''} onChange={(e)=>onEditContext({ title: e.target.value })} /></div>
                          <div>Start ISO: <input className="border rounded px-1 w-56" value={pendingContext?.start_iso ?? m.context.start_iso ?? ''} onChange={(e)=>onEditContext({ start_iso: e.target.value })} /></div>
                          <div>End ISO: <input className="border rounded px-1 w-56" value={pendingContext?.end_iso ?? m.context.end_iso ?? ''} onChange={(e)=>onEditContext({ end_iso: e.target.value })} /></div>
                          <div>Attendees: <input className="border rounded px-1 w-56" value={pendingContext?.attendees ?? m.context.attendees ?? ''} onChange={(e)=>onEditContext({ attendees: e.target.value })} /></div>
                          <div className="pt-1 flex gap-2 justify-end"><button onClick={onConfirm} className="px-3 py-1 bg-blue-600 text-white rounded">Confirm & Schedule</button></div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
            {sending ? <div className="text-xs text-gray-500">Wolfy is typing…</div> : null}
          </div>
          <div className="p-2 border-t flex gap-2">
            <input value={input} onChange={(e)=>setInput(e.target.value)} onKeyDown={(e)=>{ if(e.key==='Enter'){ onSend(); } }} className="flex-1 border rounded px-3 py-2" placeholder="Ask Wolfy… e.g., Send an email to client@example.com" />
            <button disabled={sending} onClick={onSend} className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50">Send</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default WolfyChat;


