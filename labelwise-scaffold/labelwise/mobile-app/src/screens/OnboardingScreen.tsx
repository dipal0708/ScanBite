import React, { useState } from "react";
import { View, Text, Pressable, ScrollView, StyleSheet } from "react-native";
import { saveProfile } from "../api/client";
import { colors, spacing, radii } from "../theme/theme";

const DIET_OPTIONS = [
  { key: "vegan", label: "Vegan" },
  { key: "vegan_no_roots", label: "Vegan — no roots (onion, garlic, ginger)" },
  { key: "vegetarian", label: "Vegetarian" },
  { key: "vegetarian_with_eggs", label: "Vegetarian + eggs" },
  { key: "non_vegetarian", label: "Non-vegetarian" },
];

const MEAT_OPTIONS = [
  { key: "white_meat", label: "White meat" },
  { key: "chicken", label: "Chicken" },
  { key: "red_meat", label: "Red meat" },
  { key: "pork", label: "Pork" },
  { key: "seafood", label: "Seafood" },
];

const HEALTH_FLAGS = ["Diabetes", "Hypertension", "High cholesterol", "Pregnancy", "Weight goal"];

export default function OnboardingScreen({ navigation }: any) {
  const [diet, setDiet] = useState<string | null>(null);
  const [meats, setMeats] = useState<string[]>([]);
  const [health, setHealth] = useState<string[]>([]);

  function toggle(list: string[], setList: (v: string[]) => void, key: string) {
    setList(list.includes(key) ? list.filter((k) => k !== key) : [...list, key]);
  }

  async function finish() {
    await saveProfile({ dietType: diet, meatSubprefs: meats, healthFlags: health });
    navigation.replace("Scan");
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: spacing(6) }}>
      <Text style={styles.heading}>What's your diet?</Text>
      <Text style={styles.helper}>This tunes every suggestion you'll see. Change it anytime.</Text>

      {DIET_OPTIONS.map((opt) => (
        <Pressable
          key={opt.key}
          onPress={() => setDiet(opt.key)}
          style={[styles.card, diet === opt.key && styles.cardSelected]}
        >
          <Text style={styles.cardText}>{opt.label}</Text>
        </Pressable>
      ))}

      {diet === "non_vegetarian" && (
        <>
          <Text style={styles.subheading}>Which meats do you eat?</Text>
          <View style={styles.chipRow}>
            {MEAT_OPTIONS.map((opt) => (
              <Pressable
                key={opt.key}
                onPress={() => toggle(meats, setMeats, opt.key)}
                style={[styles.chip, meats.includes(opt.key) && styles.chipSelected]}
              >
                <Text style={meats.includes(opt.key) ? styles.chipTextSelected : styles.chipText}>
                  {opt.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </>
      )}

      <Text style={styles.subheading}>Any health goals to factor in?</Text>
      <View style={styles.chipRow}>
        {HEALTH_FLAGS.map((flag) => (
          <Pressable
            key={flag}
            onPress={() => toggle(health, setHealth, flag)}
            style={[styles.chip, health.includes(flag) && styles.chipSelected]}
          >
            <Text style={health.includes(flag) ? styles.chipTextSelected : styles.chipText}>{flag}</Text>
          </Pressable>
        ))}
      </View>

      <Pressable style={[styles.button, !diet && { opacity: 0.4 }]} onPress={finish} disabled={!diet}>
        <Text style={styles.buttonText}>Start scanning</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.paper },
  heading: { fontSize: 26, fontWeight: "800", color: colors.ink },
  subheading: { fontSize: 18, fontWeight: "700", color: colors.ink, marginTop: spacing(6) },
  helper: { color: colors.muted, marginBottom: spacing(4) },
  card: {
    borderWidth: 1,
    borderColor: colors.cardBorder,
    borderRadius: radii.md,
    padding: spacing(4),
    marginBottom: spacing(2),
    backgroundColor: colors.surface,
  },
  cardSelected: { borderColor: colors.brand, backgroundColor: "#EAF3EC" },
  cardText: { fontSize: 15, color: colors.ink, fontWeight: "600" },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing(2), marginTop: spacing(2) },
  chip: {
    borderWidth: 1,
    borderColor: colors.cardBorder,
    borderRadius: radii.pill,
    paddingVertical: spacing(2),
    paddingHorizontal: spacing(4),
    backgroundColor: colors.surface,
  },
  chipSelected: { backgroundColor: colors.brand, borderColor: colors.brand },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff", fontWeight: "600" },
  button: {
    backgroundColor: colors.brand,
    borderRadius: radii.md,
    padding: spacing(4),
    alignItems: "center",
    marginTop: spacing(8),
    marginBottom: spacing(10),
  },
  buttonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
