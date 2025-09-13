import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Box,
  Divider
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  People as PeopleIcon,
  Security as SecurityIcon,
  Payment as PaymentIcon,
  Settings as SettingsIcon,
  ExitToApp as LogoutIcon
} from '@mui/icons-material';
import { useAuth } from '../services/auth';

const drawerWidth = 240;

interface MenuItemProps {
  text: string;
  icon: React.ReactNode;
  path: string;
  active?: boolean;
  onClick: () => void;
}

const MenuItem: React.FC<MenuItemProps> = ({ text, icon, active, onClick }) => {
  return (
    <ListItem disablePadding>
      <ListItemButton
        onClick={onClick}
        sx={{
          backgroundColor: active ? 'action.selected' : 'transparent',
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      >
        <ListItemIcon sx={{ color: active ? 'primary.main' : 'inherit' }}>
          {icon}
        </ListItemIcon>
        <ListItemText 
          primary={text} 
          sx={{ color: active ? 'primary.main' : 'inherit' }}
        />
      </ListItemButton>
    </ListItem>
  );
};

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const menuItems = [
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/dashboard'
    },
    {
      text: 'Пользователи',
      icon: <PeopleIcon />,
      path: '/users'
    },
    {
      text: 'Подписки',
      icon: <SecurityIcon />,
      path: '/subscriptions'
    },
    {
      text: 'Платежи',
      icon: <PaymentIcon />,
      path: '/payments'
    },
    {
      text: 'Настройки',
      icon: <SettingsIcon />,
      path: '/settings'
    }
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: {
          width: drawerWidth,
          boxSizing: 'border-box',
        },
      }}
    >
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          VPN Bot Admin
        </Typography>
      </Toolbar>
      
      <Divider />
      
      <Box sx={{ overflow: 'auto', flex: 1 }}>
        <List>
          {menuItems.map((item) => (
            <MenuItem
              key={item.path}
              text={item.text}
              icon={item.icon}
              path={item.path}
              active={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
            />
          ))}
        </List>
      </Box>

      <Divider />
      
      {/* User info and logout */}
      <Box sx={{ p: 2 }}>
        {user && (
          <Typography variant="body2" sx={{ mb: 1 }}>
            {user.username || `User ${user.telegram_id}`}
          </Typography>
        )}
        <ListItem disablePadding>
          <ListItemButton onClick={handleLogout}>
            <ListItemIcon>
              <LogoutIcon />
            </ListItemIcon>
            <ListItemText primary="Выход" />
          </ListItemButton>
        </ListItem>
      </Box>
    </Drawer>
  );
};

export default Sidebar;