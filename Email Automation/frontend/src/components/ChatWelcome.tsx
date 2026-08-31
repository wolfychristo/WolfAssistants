import React from 'react';
import { Bot, MessageSquare, Mail, Calendar, Users, Zap } from 'lucide-react';

interface ChatWelcomeProps {
  onStartChat: () => void;
}

export const ChatWelcome: React.FC<ChatWelcomeProps> = ({ onStartChat }) => {
  const features = [
    {
      icon: <Mail className="w-5 h-5" />,
      title: "Send Emails",
      description: "Draft and send professional emails automatically"
    },
    {
      icon: <Calendar className="w-5 h-5" />,
      title: "Schedule Meetings",
      description: "Book meetings and manage your calendar"
    },
    {
      icon: <Users className="w-5 h-5" />,
      title: "Manage Contacts",
      description: "Find and organize your business contacts"
    },
    {
      icon: <Zap className="w-5 h-5" />,
      title: "Business Intelligence",
      description: "Get insights and prioritize your tasks"
    }
  ];

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl mx-auto text-center">
        <div className="mb-8">
          <div className="w-16 h-16 bg-brand-red rounded-full flex items-center justify-center mx-auto mb-4">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Welcome to Wolfy</h1>
          <p className="text-neutral-300 text-lg">
            Your intelligent business co-pilot. I can help you with emails, meetings, contacts, and more.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-neutral-800 border border-neutral-700 rounded-lg p-4 text-left hover:bg-neutral-750 transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="text-brand-red">{feature.icon}</div>
                <h3 className="font-semibold text-white">{feature.title}</h3>
              </div>
              <p className="text-neutral-300 text-sm">{feature.description}</p>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white mb-4">Try asking me:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              "Send an email to John about the project update",
              "Schedule a meeting with Sarah tomorrow at 2 PM",
              "What's White's email address?",
              "Check my inbox for urgent messages",
              "Help me prioritize my tasks today",
              "Create a follow-up email for my clients"
            ].map((example, index) => (
              <button
                key={index}
                onClick={onStartChat}
                className="bg-neutral-800 hover:bg-neutral-700 border border-neutral-600 hover:border-neutral-500 rounded-lg p-3 text-left text-neutral-300 hover:text-white transition-colors text-sm"
              >
                "{example}"
              </button>
            ))}
          </div>
        </div>

        <div className="mt-8">
          <button
            onClick={onStartChat}
            className="bg-brand-red hover:bg-primary-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors flex items-center gap-2 mx-auto"
          >
            <MessageSquare className="w-5 h-5" />
            Start New Chat
          </button>
        </div>
      </div>
    </div>
  );
};
