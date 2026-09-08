import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { apiClient } from "../api/client";
import { colors, spacing, radii } from "../theme/theme";

export default function ProfileScreen() {
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    apiClient.get("/profile").then((res) => setProfile(res.data)).catch(() => {});
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Your profile</Text>
      {profile ? (
        <>
          <Row label="Diet" value={profile.diet_type} />
          <Row label="Health goals" value={(profile.health_flags || []).join(", ") || "None set"} />
          <Row label="Allergens" value={(profile.allergens || []).join(", ") || "None set"} />
        </>
      ) : (
        <Text style={styles.helper}>No profile set up yet.</Text>
      )}
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.paper, padding: spacing(6) },
  heading: { fontSize: 26, fontWeight: "800", color: colors.ink, marginBottom: spacing(6) },
  helper: { color: colors.muted },
  row: {
    borderBottomWidth: 1,
    borderBottomColor: colors.cardBorder,
    paddingVertical: spacing(3),
  },
  rowLabel: { fontSize: 12, color: colors.muted, textTransform: "uppercase" },
  rowValue: { fontSize: 16, color: colors.ink, marginTop: spacing(1) },
});
