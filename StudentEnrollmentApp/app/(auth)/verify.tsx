import React, { useState } from "react";

import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  useWindowDimensions,
} from "react-native";

import { useLocalSearchParams, useRouter } from "expo-router";

import {
  resendActivationCode,
  verifyAccount,
} from "../../src/api/api";
import {
  getApiErrorMessage,
  validateEmail,
} from "../../src/utils/validation";

export default function VerifyAccount() {
  const router = useRouter();
  const params = useLocalSearchParams<{ email?: string }>();
  const { width } = useWindowDimensions();
  const isSmallScreen = width < 480;

  const [email, setEmail] = useState(params.email || "");
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);

  const handleVerify = async () => {
    const emailError = validateEmail(email);

    if (emailError) {
      Alert.alert("Error", emailError);
      return;
    }

    if (!/^\d{6}$/.test(code.trim())) {
      Alert.alert("Error", "Enter the 6-digit verification code.");
      return;
    }

    try {
      setVerifying(true);

      const response = await verifyAccount({
        email: email.trim().toLowerCase(),
        code: code.trim(),
      });

      Alert.alert(
        "Email Verified",
        response.data?.message || "Please wait for admin activation before logging in."
      );

      router.replace("/(auth)/login" as any);
    } catch (error: any) {
      console.log("VERIFY ERROR:", error?.response?.data || error);
      Alert.alert(
        "Verification Failed",
        getApiErrorMessage(error?.response?.data, "Invalid verification code")
      );
    } finally {
      setVerifying(false);
    }
  };

  const handleResend = async () => {
    const emailError = validateEmail(email);

    if (emailError) {
      Alert.alert("Error", emailError);
      return;
    }

    try {
      setResending(true);

      const response = await resendActivationCode({
        email: email.trim().toLowerCase(),
      });

      Alert.alert(
        "Code Sent",
        response.data?.message || "A new verification code was sent."
      );
    } catch (error: any) {
      console.log("RESEND ERROR:", error?.response?.data || error);
      Alert.alert(
        "Resend Failed",
        getApiErrorMessage(error?.response?.data, "Could not resend code")
      );
    } finally {
      setResending(false);
    }
  };

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
          <Text style={styles.title}>Verify Email</Text>
          <Text style={styles.subtitle}>
            Enter the 6-digit code sent to your email.
          </Text>

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
              keyboardType="email-address"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Verification Code</Text>
            <TextInput
              style={styles.codeInput}
              placeholder="000000"
              placeholderTextColor="#94A3B8"
              value={code}
              onChangeText={(value) =>
                setCode(value.replace(/\D/g, "").slice(0, 6))
              }
              keyboardType="number-pad"
              maxLength={6}
            />
          </View>

          <TouchableOpacity
            style={[styles.primaryButton, verifying && styles.disabledButton]}
            onPress={handleVerify}
            disabled={verifying}
          >
            {verifying ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.primaryButtonText}>Verify Email</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.secondaryButton, resending && styles.disabledButton]}
            onPress={handleResend}
            disabled={resending}
          >
            {resending ? (
              <ActivityIndicator color="#1D4ED8" />
            ) : (
              <Text style={styles.secondaryButtonText}>Resend Code</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.loginLink}
            onPress={() => router.replace("/(auth)/login" as any)}
          >
            <Text style={styles.loginLinkText}>Back to Login</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  keyboardView: { flex: 1, backgroundColor: "#F8FAFC" },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: "center",
    backgroundColor: "#F8FAFC",
  },
  container: {
    width: "100%",
    maxWidth: 460,
    alignSelf: "center",
    padding: 24,
    paddingVertical: 36,
  },
  compactContainer: { paddingHorizontal: 18, paddingVertical: 28 },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: "#0F172A",
    marginBottom: 6,
  },
  subtitle: { fontSize: 15, color: "#64748B", marginBottom: 32 },
  inputGroup: { marginBottom: 18 },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: "#CBD5E1",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 15,
    color: "#0F172A",
  },
  codeInput: {
    borderWidth: 1,
    borderColor: "#CBD5E1",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 14,
    fontSize: 22,
    color: "#0F172A",
    fontWeight: "700",
    letterSpacing: 0,
    textAlign: "center",
  },
  primaryButton: {
    minHeight: 48,
    backgroundColor: "#1D4ED8",
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  primaryButtonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  secondaryButton: {
    minHeight: 48,
    backgroundColor: "#EFF6FF",
    borderWidth: 1,
    borderColor: "#BFDBFE",
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
  },
  secondaryButtonText: { color: "#1D4ED8", fontSize: 15, fontWeight: "700" },
  disabledButton: { opacity: 0.7 },
  loginLink: { alignSelf: "center", marginTop: 22 },
  loginLinkText: { color: "#475569", fontSize: 14, fontWeight: "700" },
});
