import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { login, signup } from "../api/client";
import { colors, spacing, radii } from "../theme/theme";

export default function LoginScreen({ navigation }: any) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
        navigation.replace("Scan");
      } else {
        await signup(email, password, name);
        navigation.replace("Onboarding");
      }
    } catch (err: any) {
      setError(err?.response?.data?.error || "Something went wrong.");
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>LabelWise</Text>
      <Text style={styles.subtitle}>Read the label. Know what's inside.</Text>

      {mode === "signup" && (
        <TextInput style={styles.input} placeholder="Name" value={name} onChangeText={setName} />
      )}
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable style={styles.button} onPress={handleSubmit}>
        <Text style={styles.buttonText}>{mode === "login" ? "Log in" : "Create account"}</Text>
      </Pressable>

      <Pressable onPress={() => setMode(mode === "login" ? "signup" : "login")}>
        <Text style={styles.switchText}>
          {mode === "login" ? "New here? Create an account" : "Already have an account? Log in"}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.paper, padding: spacing(6), justifyContent: "center" },
  title: { fontSize: 34, fontWeight: "800", color: colors.ink },
  subtitle: { fontSize: 15, color: colors.muted, marginTop: spacing(1), marginBottom: spacing(8) },
  input: {
    borderWidth: 1,
    borderColor: colors.cardBorder,
    borderRadius: radii.md,
    padding: spacing(3),
    marginBottom: spacing(3),
    backgroundColor: colors.surface,
  },
  button: {
    backgroundColor: colors.brand,
    borderRadius: radii.md,
    padding: spacing(4),
    alignItems: "center",
    marginTop: spacing(2),
  },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  switchText: { color: colors.brand, textAlign: "center", marginTop: spacing(4) },
  error: { color: colors.danger, marginBottom: spacing(2) },
});
