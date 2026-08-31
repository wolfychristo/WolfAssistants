import React, { useState } from 'react';
import { EnhancedChat } from '../components/EnhancedChat';
import { ChatSidebar } from '../components/ChatSidebar';

const WolfyPage: React.FC = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<number | undefined>(undefined);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  return (
    <div className="h-screen text-white flex overflow-hidden">
      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        ${sidebarCollapsed ? 'w-16' : 'w-80'} 
        ${mobileSidebarOpen ? 'fixed inset-y-0 left-0 z-50' : 'hidden lg:flex'}
        flex-col border-r border-gray-700 transition-all duration-300
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
      <div className="flex-1 flex flex-col min-w-0">
        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          <EnhancedChat mode="fullpage" selectedSessionId={selectedSessionId} />
        </div>
      </div>
    </div>
  );
};

export default WolfyPage;

