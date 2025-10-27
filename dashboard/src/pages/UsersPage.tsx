import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Modal, LoadingSpinner, Badge } from '../components/common';
import { useWebSocket } from '../hooks/useWebSocket';
import { api } from '../services/api';
import type { User, Session } from '../types';

export const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({
    email: '',
    password: '',
    broker_id: '',
    name: '',
  });

  const { isConnected } = useWebSocket('sessions', {
    onMessage: (message) => {
      if (message.type === 'session_update') {
        fetchSessions();
      }
    },
  });

  const fetchUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      await Promise.all([fetchUsers(), fetchSessions()]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const getUserSession = (userId: number): Session | undefined => {
    return sessions.find((s) => s.user_id === userId);
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createUser(createFormData);
      alert('User created successfully');
      setShowCreateModal(false);
      setCreateFormData({ email: '', password: '', broker_id: '', name: '' });
      await fetchUsers();
    } catch (error) {
      console.error('Failed to create user:', error);
      alert('Failed to create user');
    }
  };

  const handleLoginUser = async (userId: number) => {
    try {
      await api.loginUser(userId);
      alert('User logged in successfully');
      await fetchSessions();
    } catch (error) {
      console.error('Failed to login user:', error);
      alert('Failed to login user');
    }
  };

  const handleLogoutUser = async (userId: number) => {
    try {
      await api.logoutUser(userId);
      alert('User logged out successfully');
      await fetchSessions();
    } catch (error) {
      console.error('Failed to logout user:', error);
      alert('Failed to logout user');
    }
  };

  const handleDeleteUser = async (userId: number, userEmail: string) => {
    if (!confirm(`Are you sure you want to delete user ${userEmail}?`)) {
      return;
    }
    try {
      await api.deleteUser(userId);
      alert('User deleted successfully');
      await fetchUsers();
    } catch (error) {
      console.error('Failed to delete user:', error);
      alert('Failed to delete user');
    }
  };

  if (loading) {
    return <LoadingSpinner size="lg" text="Loading users..." />;
  }

  const columns = [
    {
      header: 'ID',
      accessor: 'id' as keyof User,
    },
    {
      header: 'Email',
      accessor: 'email' as keyof User,
    },
    {
      header: 'Name',
      accessor: ((row: User) => row.name || '-') as any,
    },
    {
      header: 'Broker ID',
      accessor: 'broker_id' as keyof User,
    },
    {
      header: 'Status',
      accessor: ((row: User) => {
        const session = getUserSession(row.id);
        return session ? (
          <Badge variant="success">Active</Badge>
        ) : (
          <Badge variant="gray">Inactive</Badge>
        );
      }) as any,
    },
    {
      header: 'Session Info',
      accessor: ((row: User) => {
        const session = getUserSession(row.id);
        if (!session) return '-';
        return (
          <div className="text-xs text-gray-600">
            <div>Account: {session.trading_account_id || '-'}</div>
            <div>
              Logged in:{' '}
              {session.login_at
                ? new Date(session.login_at).toLocaleString()
                : '-'}
            </div>
          </div>
        );
      }) as any,
    },
    {
      header: 'Actions',
      accessor: ((row: User) => {
        const session = getUserSession(row.id);
        return (
          <div className="flex gap-2">
            {session ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleLogoutUser(row.id)}
              >
                Logout
              </Button>
            ) : (
              <Button
                size="sm"
                variant="primary"
                onClick={() => handleLoginUser(row.id)}
              >
                Login
              </Button>
            )}
            <Button
              size="sm"
              variant="danger"
              onClick={() => handleDeleteUser(row.id, row.email)}
            >
              Delete
            </Button>
          </div>
        );
      }) as any,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
          <p className="text-gray-600 mt-1">
            Manage trading accounts and sessions
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowCreateModal(true)}>
          + Create User
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Users</p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {users.length}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-2xl">
              👥
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Active Sessions
              </p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {sessions.length}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-green-50 text-green-600 flex items-center justify-center text-2xl">
              🔌
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                WebSocket Status
              </p>
              <p className="text-2xl font-bold text-gray-900 mt-2">
                {isConnected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
            <div
              className={`w-12 h-12 rounded-lg ${
                isConnected
                  ? 'bg-green-50 text-green-600'
                  : 'bg-red-50 text-red-600'
              } flex items-center justify-center text-2xl`}
            >
              {isConnected ? '✅' : '❌'}
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <Card title="Users">
        <Table data={users} columns={columns} />
      </Card>

      {/* Create User Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New User"
        footer={
          <>
            <Button
              variant="secondary"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" onClick={handleCreateUser}>
              Create User
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreateUser} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              required
              className="input"
              value={createFormData.email}
              onChange={(e) =>
                setCreateFormData({ ...createFormData, email: e.target.value })
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password *
            </label>
            <input
              type="password"
              required
              className="input"
              value={createFormData.password}
              onChange={(e) =>
                setCreateFormData({
                  ...createFormData,
                  password: e.target.value,
                })
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Broker ID *
            </label>
            <input
              type="text"
              required
              className="input"
              value={createFormData.broker_id}
              onChange={(e) =>
                setCreateFormData({
                  ...createFormData,
                  broker_id: e.target.value,
                })
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name (Optional)
            </label>
            <input
              type="text"
              className="input"
              value={createFormData.name}
              onChange={(e) =>
                setCreateFormData({ ...createFormData, name: e.target.value })
              }
            />
          </div>
        </form>
      </Modal>
    </div>
  );
};
