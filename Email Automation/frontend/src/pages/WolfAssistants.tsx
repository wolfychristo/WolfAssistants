import React, { useState } from 'react';
import { EnhancedChat } from '../components/EnhancedChat';
import { ChatSidebar } from '../components/ChatSidebar';
import { Button } from '../components/ui/button';
import { Menu, X, Bot } from 'lucide-react';

const WolfAssistantsPage: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<number | undefined>(undefined);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen(!mobileSidebarOpen);
  };

  return (
    <div className="h-screen bg-brand-white text-brand-black flex overflow-hidden">
      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div 
          className="fixed inset-0 bg-brand-black bg-opacity-20 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${sidebarCollapsed ? 'w-16' : 'w-80'} 
        ${mobileSidebarOpen ? 'fixed inset-y-0 left-0 z-50' : 'hidden lg:flex'}
        flex-col bg-brand-white border-r border-gray-100 transition-all duration-500 shadow-sm
      `}>
        <ChatSidebar
          onSelectSession={(session: { id: number }) => { setSelectedSessionId(session.id); setMobileSidebarOpen(false); }}
          onNewSession={() => setMobileSidebarOpen(false)}
          currentSessionId={selectedSessionId}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebar}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-brand-gray/30">
        {/* Top Bar */}
        <div className="bg-brand-white border-b border-gray-100 px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-4">
            <Button
              size="sm"
              variant="ghost"
              className="lg:hidden text-gray-400 hover:text-brand-black"
              onClick={toggleMobileSidebar}
            >
              <Menu className="w-5 h-5" />
            </Button>
            
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-brand-black flex items-center justify-center rounded-lg shadow-lg">
                <Bot className="w-5 h-5 text-brand-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-brand-black tracking-tight">WolfAssistants</h1>
                <p className="text-[10px] font-black uppercase tracking-widest text-brand-red">Elite Intelligence</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              className="hidden lg:flex text-gray-400 hover:text-brand-black transition-colors"
              onClick={toggleSidebar}
            >
              {sidebarCollapsed ? <Menu className="w-5 h-5" /> : <X className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden p-4">
          <div className="h-full bg-brand-white rounded-3xl border border-gray-100 shadow-xl overflow-hidden">
            <EnhancedChat mode="fullpage" selectedSessionId={selectedSessionId} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default WolfAssistantsPage;


