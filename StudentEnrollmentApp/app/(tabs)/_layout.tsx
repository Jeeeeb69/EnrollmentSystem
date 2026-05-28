import { Tabs, useRouter } from 'expo-router';
import React, { useEffect, useState } from 'react';
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';
import { tokenStorage } from '../../src/api/storage';
import { getCurrentUser } from '../../src/api/session';

export default function TabLayout() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isWideLayout = width >= 900;
  const isCompactPhone = width < 380;
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const loadCurrentUser = async () => {
      try {
        const user = await getCurrentUser();

        if (isMounted) {
          setIsAdmin(user.is_staff);
        }
      } catch {
        if (isMounted) {
          setIsAdmin(false);
        }
      }
    };

    loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogout = async () => {
    await tokenStorage.removeAuthTokens();

    router.replace('/(auth)/login');
  };

  return (
    <Tabs
      initialRouteName="dashboard"
      screenOptions={{
        headerShown: false,
        tabBarHideOnKeyboard: true,
        tabBarPosition: isWideLayout ? 'left' : 'bottom',
        tabBarLabelPosition: isWideLayout ? 'beside-icon' : 'below-icon',
        tabBarShowLabel: isWideLayout,
        tabBarActiveTintColor: '#2563EB',
        tabBarInactiveTintColor: '#64748B',
        tabBarActiveBackgroundColor: '#EFF6FF',
        tabBarInactiveBackgroundColor: '#FFFFFF',
        tabBarStyle: isWideLayout ? styles.sidebar : styles.mobileTabBar,
        tabBarItemStyle: isWideLayout
          ? styles.sidebarItem
          : [
              styles.mobileTabItem,
              isCompactPhone && styles.compactMobileTabItem,
            ],
        tabBarLabelStyle: styles.sidebarLabel,
        tabBarIconStyle: isWideLayout
          ? styles.sidebarIcon
          : styles.mobileTabIcon,
        tabBarBackground: () => (
          isWideLayout ? (
            <View pointerEvents="none" style={styles.sidebarBackground}>
              <Text style={styles.sidebarTitle}>NAVIGATION</Text>
              <View style={styles.sidebarDivider} />
            </View>
          ) : (
            <View pointerEvents="none" style={styles.mobileTabBackground} />
          )
        ),
      }}
    >
      <Tabs.Screen name="index" options={{ href: null }} />
      <Tabs.Screen name="dashboard" options={{ title: 'Dashboard', tabBarIcon: ({ color, size }) => <Ionicons name="home-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="students" options={{ href: isAdmin ? undefined : null, title: 'Students', tabBarIcon: ({ color, size }) => <Ionicons name="people-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="subjects" options={{ title: 'Subjects', tabBarIcon: ({ color, size }) => <Ionicons name="book-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="sections" options={{ title: 'Sections', tabBarIcon: ({ color, size }) => <Ionicons name="briefcase-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="enrollments" options={{ title: 'Enrollments', tabBarIcon: ({ color, size }) => <Ionicons name="clipboard-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="chatbot" options={{ title: 'WebSocket Chat', tabBarIcon: ({ color, size }) => <Ionicons name="chatbubble-ellipses-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" size={size} color={color} /> }} />
      <Tabs.Screen
        name="logout"
        options={{
          title: 'Logout',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="log-out-outline" size={size} color={color} />
          ),
          tabBarButton: ({ children, style }) => (
            <Pressable
              accessibilityRole="button"
              style={style}
              onPress={handleLogout}
            >
              {children}
            </Pressable>
          ),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  sidebar: {
    width: 184,
    backgroundColor: '#FFFFFF',
    borderRightWidth: 1,
    borderRightColor: '#E5EAF2',
    paddingTop: 70,
    paddingHorizontal: 8,
    paddingBottom: 18,
  },

  sidebarBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFFFF',
  },

  sidebarTitle: {
    color: '#94A3B8',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0,
    marginLeft: 12,
    marginTop: 22,
  },

  sidebarDivider: {
    height: 1,
    backgroundColor: '#EEF2F7',
    marginTop: 18,
  },

  sidebarItem: {
    height: 40,
    borderRadius: 8,
    marginHorizontal: 0,
    marginVertical: 3,
    paddingHorizontal: 10,
  },

  sidebarIcon: {
    marginRight: 8,
  },

  sidebarLabel: {
    fontSize: 13,
    fontWeight: '700',
  },

  mobileTabBar: {
    height: Platform.OS === 'ios' ? 76 : 68,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E5EAF2',
    paddingTop: 7,
    paddingBottom: Platform.OS === 'ios' ? 16 : 8,
  },

  mobileTabBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#FFFFFF',
  },

  mobileTabItem: {
    minWidth: 44,
    borderRadius: 8,
    marginHorizontal: 0,
  },

  compactMobileTabItem: {
    minWidth: 38,
  },

  mobileTabIcon: {
    marginRight: 0,
  },
});
