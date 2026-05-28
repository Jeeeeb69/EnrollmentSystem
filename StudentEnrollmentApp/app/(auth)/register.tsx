import React, { useState } from "react";

import {
  View,
  Text,
  TextInput,
  ScrollView,
  Alert,
  StyleSheet,
  TouchableOpacity,
  Platform,
  ActivityIndicator,
  useWindowDimensions,
} from "react-native";

import { Picker } from "@react-native-picker/picker";
import DateTimePicker from "@react-native-community/datetimepicker";

import { useRouter } from "expo-router";
import Ionicons from "@expo/vector-icons/Ionicons";

import { api } from "../../src/api/api";
import {
  cleanText,
  courses,
  firstValidationError,
  getApiErrorMessage,
  semesters,
  validateBirthday,
  validateEmail,
  validateName,
  validatePassword,
  validatePhone,
  validateStudentNumber,
  yearLevels,
} from "../../src/utils/validation";

const formatDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
};

export default function Register() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const isSmallScreen = width < 480;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rePassword, setRePassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showRePassword, setShowRePassword] = useState(false);

  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [studentNumber, setStudentNumber] = useState("");

  const [parentName, setParentName] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [homeAddress, setHomeAddress] = useState("");

  const [birthday, setBirthday] = useState<Date | null>(null);
  const [birthdayValue, setBirthdayValue] = useState("");
  const [showDatePicker, setShowDatePicker] = useState(false);

  const [course, setCourse] = useState("");
  const [yearLevel, setYearLevel] = useState("");
  const [semester, setSemester] = useState("");

  const [loading, setLoading] = useState(false);
  const [formMessage, setFormMessage] = useState("");

  const onChangeBirthday = (event: any, selectedDate?: Date) => {
    setShowDatePicker(false);

    if (selectedDate && !isNaN(selectedDate.getTime())) {
      setBirthday(selectedDate);
      setBirthdayValue(formatDate(selectedDate));
    }
  };

  const handleRegister = async () => {
    setFormMessage("");

    const validationMessage = firstValidationError([
      validateName(firstName, "First name"),
      validateName(middleName, "Middle name", false),
      validateName(lastName, "Last name"),
      validateStudentNumber(studentNumber),
      validateName(parentName, "Parent name", false),
      validatePhone(contactNumber),
      homeAddress.length > 500 ? "Home address must be 500 characters or fewer." : "",
      validateBirthday(birthdayValue),
      course ? "" : "Course is required.",
      yearLevel ? "" : "Year level is required.",
      semester ? "" : "Semester is required.",
      validateEmail(email),
      validatePassword(password),
    ]);

    if (validationMessage) {
      setFormMessage(validationMessage);
      Alert.alert("Error", validationMessage);
      return;
    }

    if (password !== rePassword) {
      const message = "Passwords do not match";
      setFormMessage(message);
      Alert.alert("Error", message);
      return;
    }

    try {
      setLoading(true);

      const formattedBirthday = birthdayValue.trim() || null;

      const payload = {
        email: email.trim().toLowerCase(),
        password,

        first_name: cleanText(firstName),
        middle_name: cleanText(middleName),
        last_name: cleanText(lastName),

        student_number: cleanText(studentNumber).toUpperCase(),

        parent_name: cleanText(parentName),
        contact_number: cleanText(contactNumber),
        home_address: cleanText(homeAddress),

        birthday: formattedBirthday,

        course,
        year_level: yearLevel,
        semester,
      };

      const registerRes = await api.post("auth/register/", payload);

      const message =
        registerRes.data?.message ||
        `Account created but not activated yet. Auto-enrolled ${registerRes.data.auto_enrolled_count || 0} subject(s). ${registerRes.data.waitlisted_count || 0} waitlisted.`;
      const verificationCode = registerRes.data?.verification_code
        ? `\n\nVerification code: ${registerRes.data.verification_code}`
        : "";

      Alert.alert("Verify Your Email", `${message}${verificationCode}`);

      router.replace({
        pathname: "/(auth)/verify",
        params: {
          email: email.trim().toLowerCase(),
          code: registerRes.data?.verification_code || "",
        },
      } as any);
    } catch (error: any) {
      console.log(
        "REGISTER ERROR:",
        error.response?.data || error
      );

      const msg =
        (error?.code === "ECONNABORTED"
          ? "Connection timed out. Make sure Django is running and the app is using the correct API address."
          : "") ||
        (error?.message === "Network Error"
          ? "Cannot connect to the server. Make sure Django is running on 0.0.0.0:8000 and your phone/computer can reach the API address."
          : "") ||
        getApiErrorMessage(
          error.response?.data,
          "Registration failed"
        );

      setFormMessage(msg);
      Alert.alert("Error", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={[
        styles.container,
        isSmallScreen && styles.compactContainer,
      ]}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={styles.title}>Student Registration</Text>

      <TextInput placeholder="First Name *" style={styles.input} onChangeText={setFirstName} />
      <TextInput placeholder="Middle Name" style={styles.input} onChangeText={setMiddleName} />
      <TextInput placeholder="Last Name *" style={styles.input} onChangeText={setLastName} />
      <TextInput placeholder="Student Number *" style={styles.input} onChangeText={setStudentNumber} />
      <TextInput placeholder="Parent Name" style={styles.input} onChangeText={setParentName} />
      <TextInput placeholder="Contact Number" style={styles.input} onChangeText={setContactNumber} />
      <TextInput placeholder="Home Address" style={styles.input} onChangeText={setHomeAddress} />

      {Platform.OS === "web" ? (
        <input
          type="date"
          value={birthdayValue}
          max={formatDate(new Date())}
          onChange={(e) => {
            setBirthdayValue(e.currentTarget.value);
          }}
          style={{
            padding: 12,
            border: "1px solid #ccc",
            borderRadius: 8,
            marginBottom: 12,
            width: "100%",
          }}
        />
      ) : (
        <>
          <TouchableOpacity
            style={styles.dateInput}
            onPress={() => setShowDatePicker(true)}
          >
            <Text>
              {birthday
                ? birthdayValue
                : "Select Birthday"}
            </Text>
          </TouchableOpacity>

          {showDatePicker && (
            <DateTimePicker
              value={birthday || new Date()}
              mode="date"
              maximumDate={new Date()}
              onChange={onChangeBirthday}
            />
          )}
        </>
      )}

      <View style={styles.pickerContainer}>
        <Picker selectedValue={course} onValueChange={setCourse}>
          <Picker.Item label="Select Course *" value="" />
          {courses.map((item) => (
            <Picker.Item key={item} label={item} value={item} />
          ))}
        </Picker>
      </View>

      <View style={styles.pickerContainer}>
        <Picker selectedValue={yearLevel} onValueChange={setYearLevel}>
          <Picker.Item label="Select Year *" value="" />
          {yearLevels.map((item) => (
            <Picker.Item key={item} label={item} value={item} />
          ))}
        </Picker>
      </View>

      <View style={styles.pickerContainer}>
        <Picker selectedValue={semester} onValueChange={setSemester}>
          <Picker.Item label="Select Semester *" value="" />
          {semesters.map((item) => (
            <Picker.Item key={item} label={item} value={item} />
          ))}
        </Picker>
      </View>

      <TextInput placeholder="Email *" style={styles.input} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
      <View style={styles.passwordField}>
        <TextInput
          placeholder="Password *"
          secureTextEntry={!showPassword}
          style={styles.passwordInput}
          onChangeText={setPassword}
          autoCapitalize="none"
          autoCorrect={false}
          textContentType="newPassword"
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

      <View style={styles.passwordField}>
        <TextInput
          placeholder="Confirm Password *"
          secureTextEntry={!showRePassword}
          style={styles.passwordInput}
          onChangeText={setRePassword}
          autoCapitalize="none"
          autoCorrect={false}
          textContentType="newPassword"
        />
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel={showRePassword ? "Hide confirm password" : "Show confirm password"}
          style={styles.passwordToggle}
          onPress={() => setShowRePassword((current) => !current)}
        >
          <Ionicons
            name={showRePassword ? "eye-off-outline" : "eye-outline"}
            size={20}
            color="#64748B"
          />
        </TouchableOpacity>
      </View>

      {formMessage ? (
        <Text style={styles.formMessage}>{formMessage}</Text>
      ) : null}

      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel="Register"
        activeOpacity={0.85}
        disabled={loading}
        onPress={handleRegister}
        style={[styles.registerButton, loading && styles.disabledButton]}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.registerButtonText}>Register</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#fff" },
  container: {
    flexGrow: 1,
    width: "100%",
    maxWidth: 720,
    alignSelf: "center",
    padding: 24,
    paddingBottom: 90,
    backgroundColor: "#fff",
  },
  compactContainer: { paddingHorizontal: 16, paddingTop: 18 },
  title: { fontSize: 28, fontWeight: "bold", marginBottom: 20, textAlign: "center" },
  input: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 12, marginBottom: 12 },
  passwordField: {
    minHeight: 46,
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#ccc",
    borderRadius: 8,
    marginBottom: 12,
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  passwordToggle: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  pickerContainer: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, marginBottom: 12, overflow: "hidden" },
  dateInput: { borderWidth: 1, borderColor: "#ccc", borderRadius: 8, padding: 14, marginBottom: 12 },
  formMessage: {
    color: "#B91C1C",
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
  },
  registerButton: {
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1D4ED8",
    borderRadius: 8,
  },
  disabledButton: {
    opacity: 0.7,
  },
  registerButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
  },
});
