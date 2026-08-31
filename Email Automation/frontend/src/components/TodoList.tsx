import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Check, Clock, AlertCircle, Calendar, Search, ChevronDown, ChevronUp } from 'lucide-react';
import { todosAPI } from '../services/api';
import { Todo } from '../types';
import toast from 'react-hot-toast';
import { format, parseISO } from 'date-fns';

interface TodoListProps {
  className?: string;
}

const TodoList: React.FC<TodoListProps> = ({ className = '' }) => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingTodo, setEditingTodo] = useState<Todo | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPriority, setFilterPriority] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [filterStatus, setFilterStatus] = useState<'all' | 'completed' | 'pending'>('all');
  const [sortBy, setSortBy] = useState<'created' | 'due_date' | 'priority' | 'title'>('created');
  const [expandedDescriptions, setExpandedDescriptions] = useState<Set<number>>(new Set());
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    due_date: '',
    priority: 'medium' as 'low' | 'medium' | 'high'
  });

  const loadTodos = async () => {
    try {
      setIsLoading(true);
      const res = await todosAPI.getAll();
      // Ensure we always set an array, even if the response is unexpected
      const todosData = Array.isArray(res.data) ? res.data : [];
      setTodos(todosData);
    } catch (e) {
      console.error('Error loading todos:', e);
      toast.error('Failed to load todos');
      setTodos([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTodos();
  }, []);

  const handleAddTodo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;

    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        due_date: formData.due_date || undefined,
        priority: formData.priority
      };
      
      const res = await todosAPI.create(payload);
      setTodos([res.data, ...(Array.isArray(todos) ? todos : [])]);
      setShowAddForm(false);
      setFormData({ title: '', description: '', due_date: '', priority: 'medium' });
      toast.success('Todo added');
    } catch (e: any) {
      console.error('Error creating todo:', e);
      toast.error(e?.response?.data?.detail || 'Failed to add todo');
    }
  };

  const handleUpdateTodo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTodo || !formData.title.trim()) return;

    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        due_date: formData.due_date || undefined,
        priority: formData.priority
      };
      
      const res = await todosAPI.update(editingTodo.id, payload);
      setTodos((Array.isArray(todos) ? todos : []).map(t => t.id === editingTodo.id ? res.data : t));
      setEditingTodo(null);
      setFormData({ title: '', description: '', due_date: '', priority: 'medium' });
      toast.success('Todo updated');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to update todo');
    }
  };

  const handleToggleTodo = async (id: number) => {
    try {
      if (!id || id === undefined) {
        console.error('Invalid todo ID:', id);
        toast.error('Invalid todo ID');
        return;
      }
      const res = await todosAPI.toggle(id);
      setTodos((Array.isArray(todos) ? todos : []).map(t => t.id === id ? res.data : t));
    } catch (e: any) {
      console.error('Error toggling todo:', e);
      toast.error(e?.response?.data?.detail || 'Failed to toggle todo');
    }
  };

  const handleDeleteTodo = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this todo?')) return;
    
    try {
      await todosAPI.delete(id);
      setTodos((Array.isArray(todos) ? todos : []).filter(t => t.id !== id));
      toast.success('Todo deleted');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Failed to delete todo');
    }
  };

  const toggleDescription = (todoId: number) => {
    const newExpanded = new Set(expandedDescriptions);
    if (newExpanded.has(todoId)) {
      newExpanded.delete(todoId);
    } else {
      newExpanded.add(todoId);
    }
    setExpandedDescriptions(newExpanded);
  };

  const startEdit = (todo: Todo) => {
    setEditingTodo(todo);
    setFormData({
      title: todo.title,
      description: todo.description || '',
      due_date: todo.due_date ? todo.due_date.split('T')[0] : '',
      priority: todo.priority
    });
  };

  const cancelEdit = () => {
    setEditingTodo(null);
    setShowAddForm(false);
    setFormData({ title: '', description: '', due_date: '', priority: 'medium' });
  };

  // Filter and sort todos
  const filteredAndSortedTodos = React.useMemo(() => {
    if (!todos || !Array.isArray(todos)) {
      return [];
    }
    let filtered = todos.filter(todo => {
      const matchesSearch = todo.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (todo.description && todo.description.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesPriority = filterPriority === 'all' || todo.priority === filterPriority;
      const matchesStatus = filterStatus === 'all' || 
                           (filterStatus === 'completed' && todo.completed) ||
                           (filterStatus === 'pending' && !todo.completed);
      
      return matchesSearch && matchesPriority && matchesStatus;
    });

    // Sort todos
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'due_date':
          if (!a.due_date && !b.due_date) return 0;
          if (!a.due_date) return 1;
          if (!b.due_date) return -1;
          return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
        case 'priority':
          const priorityOrder = { 'high': 1, 'medium': 2, 'low': 3 };
          return priorityOrder[a.priority] - priorityOrder[b.priority];
        case 'title':
          return a.title.localeCompare(b.title);
        case 'created':
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });

    return filtered;
  }, [todos, searchTerm, filterPriority, filterStatus, sortBy]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high': return <AlertCircle className="w-3 h-3" />;
      case 'medium': return <Clock className="w-3 h-3" />;
      case 'low': return <Check className="w-3 h-3" />;
      default: return <Clock className="w-3 h-3" />;
    }
  };

  const isOverdue = (dueDate: string | null) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date() && new Date(dueDate).toDateString() !== new Date().toDateString();
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-100 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Check className="w-5 h-5 mr-2 text-blue-600" />
            My Tasks
          </h3>
          <button
            onClick={() => setShowAddForm(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm flex items-center space-x-2 transition-all duration-200 shadow-sm hover:shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>Add Task</span>
          </button>
        </div>

        {/* Search and Filters */}
        <div className="space-y-3">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Priorities</option>
              <option value="high">High Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="low">Low Priority</option>
            </select>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Tasks</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="created">Sort by Created</option>
              <option value="due_date">Sort by Due Date</option>
              <option value="priority">Sort by Priority</option>
              <option value="title">Sort by Title</option>
            </select>
          </div>
        </div>
      </div>

      {/* Fixed-height scrollable list */}
      <div className="relative h-80 overflow-y-auto pr-2 scrollbar-thin">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading tasks...</p>
          </div>
        ) : filteredAndSortedTodos.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Check className="w-12 h-12 mx-auto text-gray-300 mb-4" />
            <p className="text-sm">No tasks found</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredAndSortedTodos.map((todo) => {
              const isExpanded = expandedDescriptions.has(todo.id);
              const description = todo.description || '';
              const wordCount = description.split(' ').length;
              const shouldTruncate = wordCount > 20; // Allow more words for 3-5 lines
              const displayDescription = shouldTruncate && !isExpanded 
                ? description.split(' ').slice(0, 20).join(' ') + '...' 
                : description;

              return (
                <div key={todo.id} className={`p-4 transition-all duration-200 hover:bg-gray-50 ${
                  todo.completed ? 'opacity-75' : ''
                }`}>
                  <div className="flex items-start space-x-3">
                    <button
                      onClick={() => handleToggleTodo(todo.id)}
                      className={`mt-1 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        todo.completed
                          ? 'bg-green-500 border-green-500 text-white'
                          : 'border-gray-300 hover:border-green-500'
                      }`}
                    >
                      {todo.completed && <Check className="w-3 h-3" />}
                    </button>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className={`text-sm font-medium ${
                          todo.completed ? 'line-through text-gray-500' : 'text-gray-900'
                        }`}>
                          {todo.title}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityColor(todo.priority)}`}>
                          {getPriorityIcon(todo.priority)}
                          <span className="ml-1 capitalize">{todo.priority}</span>
                        </span>
                      </div>
                      
                      {description && (
                        <div className="mb-2">
                          <p className={`text-xs text-gray-600 leading-relaxed break-words ${
                            todo.completed ? 'line-through' : ''
                          }`} style={{ 
                            maxWidth: '100%',
                            wordWrap: 'break-word',
                            overflowWrap: 'break-word',
                            hyphens: 'auto'
                          }}>
                            {displayDescription}
                          </p>
                          {shouldTruncate && (
                            <button
                              onClick={() => toggleDescription(todo.id)}
                              className="text-xs text-blue-600 hover:text-blue-800 mt-1 flex items-center space-x-1"
                            >
                              <span>{isExpanded ? 'Read Less' : 'Read More'}</span>
                              {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          )}
                        </div>
                      )}
                      
                      <div className="flex items-center space-x-3 text-xs text-gray-500">
                        {todo.due_date && (
                          <div className={`flex items-center space-x-1 ${
                            isOverdue(todo.due_date) ? 'text-red-600' : ''
                          }`}>
                            <Calendar className="w-3 h-3" />
                            <span>{format(parseISO(todo.due_date), 'MMM dd, yyyy')}</span>
                            {isOverdue(todo.due_date) && <span className="text-red-600">(Overdue)</span>}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex space-x-2">
                      <button
                        onClick={() => startEdit(todo)}
                        className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
                        title="Edit task"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteTodo(todo.id)}
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete task"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>


      {/* Add/Edit Form Modal */}
      {(showAddForm || editingTodo) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-medium text-gray-900">
                {editingTodo ? 'Edit Task' : 'Add New Task'}
              </h3>
            </div>
            
            <form onSubmit={editingTodo ? handleUpdateTodo : handleAddTodo} className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter task title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter task description (optional)"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value as 'low' | 'medium' | 'high' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={cancelEdit}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  {editingTodo ? 'Update' : 'Add'} Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TodoList;
