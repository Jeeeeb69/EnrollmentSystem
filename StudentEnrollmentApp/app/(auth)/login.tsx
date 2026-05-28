import React, {
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  Alert,
  ScrollView,
  ActivityIndicator,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  useWindowDimensions,
} from "react-native";
import { useRouter } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";

import {
  loginStudent,
  LoginResponse,
} from "../../src/api/api";
import { getCurrentUser } from "../../src/api/session";
import { tokenStorage } from "../../src/api/storage";
import {
  getApiErrorMessage,
  validateEmail,
} from "../../src/utils/validation";

export default function Login() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isSmallScreen = width < 480;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  // Check Existing Login
  const checkToken = useCallback(async () => {
    try {
      const token = await tokenStorage.getItem("accessToken");
      if (token) {
        await getCurrentUser();
        router.replace("/(tabs)/dashboard" as any);
      }
    } catch (error) {
      console.log("TOKEN CHECK ERROR:", error);
      await tokenStorage.removeAuthTokens();
    } finally {
      setCheckingAuth(false);
    }
  }, [router]);

  useEffect(() => {
    checkToken();
  }, [checkToken]);

  // Login Function
  const handleLogin = async () => {
    const emailError = validateEmail(email);

    if (emailError) {
      Alert.alert("Error", emailError);
      return;
    }

    if (!password) {
      Alert.alert("Error", "Password is required.");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        email: email.trim().toLowerCase(),
        password,
      };

      const response = await loginStudent(payload);
      const tokens: LoginResponse = response.data;

      // Save tokens
      await tokenStorage.setItem("accessToken", tokens.access);
      await tokenStorage.setItem("refreshToken", tokens.refresh);

      Alert.alert("Success", "Logged in successfully!");

      router.replace("/(tabs)/dashboard" as any);
    } catch (error: any) {
      console.log("LOGIN ERROR:", error?.response?.data || error?.message);
      const msg =
        (error?.code === "ECONNABORTED"
          ? "Connection timed out. Make sure your phone and computer are on the same Wi-Fi and Django is running."
          : "") ||
        (error?.message === "Network Error"
          ? "Cannot connect to the server. Make sure Django is running on 0.0.0.0:8000 and your phone is on the same Wi-Fi."
          : "") ||
        getApiErrorMessage(error?.response?.data, "Invalid credentials");

      const lowerMsg = msg.toLowerCase();

      if (lowerMsg.includes("verify your email") || lowerMsg.includes("verification code")) {
        Alert.alert("Login Denied", msg, [
          { text: "Cancel", style: "cancel" },
          {
            text: "Verify",
            onPress: () =>
              router.push({
                pathname: "/(auth)/verify",
                params: { email: email.trim().toLowerCase() },
              } as any),
          },
        ]);
      } else {
        Alert.alert("Login Error", msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // Show loading screen while checking token
  if (checkingAuth) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1D4ED8" />
        <Text style={styles.loadingText}>Checking authentication...</Text>
      </View>
    );
  }

  // Render login screen
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.keyboardView}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContainer}
        keyboardShouldPersistTaps="handled"
      >
        <View
          style={[
            styles.container,
            isSmallScreen && styles.compactContainer,
          ]}
        >
          <Text style={styles.title}>Welcome Back</Text>
          <Text style={styles.subtitle}>Login to continue</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Email</Text>
            <TextInput
              style={styles.input}
              placeholder="Enter your email"
              placeholderTextColor="#94A3B8"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              keyboardType="email-address"
              textContentType="emailAddress"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.passwordField}>
              <TextInput
                style={styles.passwordInput}
                placeholder="Enter your password"
                placeholderTextColor="#94A3B8"
                value={password}
                onChangeText={setPassword}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="password"
                textContentType="password"
                secureTextEntry={!showPassword}
              />

              <TouchableOpacity
                accessibilityRole="button"
                accessibilityLabel={showPassword ? "Hide password" : "Show password"}
                style={styles.passwordToggle}
                onPress={() => setShowPassword((current) => !current)}
              >
                <Ionicons
                  name={showPassword ? "eye-off-outline" : "eye-outline"}
                  size={20}
                  color="#64748B"
                />
              </TouchableOpacity>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.loginButton, loading && { opacity: 0.7 }]}
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.loginButtonText}>Login</Text>}
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.push("/(auth)/register" as any)} style={styles.registerContainer}>
            <Text style={styles.registerText}>
              {"Don't have an account?"}
            </Text>
            <Text style={styles.registerLink}>Register</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  keyboardView: { flex: 1, backgroundColor: "#F8FAFC" },
  scrollContainer: { flexGrow: 1, backgroundColor: "#F8FAFC" },
  container: {
    flex: 1,
    justifyContent: "center",
    width: "100%",
    maxWidth: 460,
    alignSelf: "center",
    padding: 24,
    paddingVertical: 36,
  },
  compactContainer: { paddingHorizontal: 18, paddingVertical: 28 },
  title: { fontSize: 32, fontWeight: "700", color: "#0F172A", marginBottom: 6 },
  subtitle: { fontSize: 15, color: "#64748B", marginBottom: 32 },
  inputGroup: { marginBottom: 18 },
  label: { fontSize: 14, fontWeight: "600", color: "#334155", marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: "#CBD5E1",
    backgroundColor: "#fff",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 15,
    color: "#0F172A",
  },
  passwordField: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#CBD5E1",
    backgroundColor: "#fff",
    borderRadius: 12,
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 15,
    color: "#0F172A",
  },
  passwordToggle: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  loginButton: { backgroundColor: "#1D4ED8", paddingVertical: 15, borderRadius: 12, alignItems: "center", justifyContent: "center", marginTop: 10 },
  loginButtonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  registerContainer: { flexDirection: "row", justifyContent: "center", marginTop: 24 },
  registerText: { color: "#64748B", fontSize: 14 },
  registerLink: { color: "#1D4ED8", fontSize: 14, fontWeight: "700", marginLeft: 5 },
  loadingContainer: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#F8FAFC" },
  loadingText: { marginTop: 12, color: "#64748B", fontSize: 14 },
});
