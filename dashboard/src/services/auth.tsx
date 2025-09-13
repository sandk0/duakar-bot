import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiService from './api';

interface User {
  id: number;
  username: string;
  telegram_id: number;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          // Verify token with backend
          const response = await apiService.get('/auth/me');
          setUser(response.data);
        } catch (error) {
          localStorage.removeItem('auth_token');
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await apiService.login(username, password);
      
      if (response.success) {
        localStorage.setItem('auth_token', response.data.token);
        setUser(response.data.user);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
    // Optionally call backend logout endpoint
    apiService.logout().catch(console.error);
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
  };

  if (isLoading) {
    return <div>Loading...</div>; // You can replace this with a loading spinner component
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};