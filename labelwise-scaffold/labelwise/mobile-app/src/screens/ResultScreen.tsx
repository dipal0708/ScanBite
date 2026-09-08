import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { apiClient } from "../api/client";
import { colors, spacing, radii } from "../theme/theme";

export default function ResultScreen({ route }: any) {
  const { scanId } = route.params;
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    apiClient.get(`/scans/${scanId}`).then((res) => setResult(res.data));
  }, [scanId]);

  if (!result) return <View style={styles.container} />;

  const score = result.label_score ?? 0;
  const scoreColor = score >= 70 ? colors.good : score >= 40 ? colors.warning : colors.danger;

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: spacing(6) }}>
      <View style={[styles.scoreCard, { borderColor: scoreColor }]}>
        <Text style={styles.scoreLabel}>Label Score</Text>
        <Text style={[styles.scoreNumber, { color: scoreColor }]}>{score}</Text>
      </View>

      <Text style={styles.summary}>{result.ai_summary}</Text>

      <Text style={styles.sectionTitle}>Flags for you</Text>
      {(result.flags || []).map((f: any, i: number) => (
        <View key={i} style={styles.flagRow}>
          <Text style={styles.flagIngredient}>{f.ingredient}</Text>
          <Text style={styles.flagReason}>{f.reason}</Text>
        </View>
      ))}

      <Text style={styles.sectionTitle}>Suggestions</Text>
      {(result.ai_suggestions || []).map((s: string, i: number) => (
        <Text key={i} style={styles.suggestion}>
          •  {s}
        </Text>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.paper },
  scoreCard: {
    borderWidth: 3,
    borderRadius: radii.md,
    padding: spacing(6),
    alignItems: "center",
    backgroundColor: colors.surface,
    marginBottom: spacing(6),
  },
  scoreLabel: { fontSize: 13, color: colors.muted, fontWeight: "600" },
  scoreNumber: { fontSize: 56, fontWeight: "800" },
  summary: { fontSize: 16, color: colors.ink, lineHeight: 22, marginBottom: spacing(6) },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: colors.ink, marginTop: spacing(4), marginBottom: spacing(2) },
  flagRow: {
    borderLeftWidth: 3,
    borderLeftColor: colors.danger,
    paddingLeft: spacing(3),
    marginBottom: spacing(3),
  },
  flagIngredient: { fontWeight: "700", color: colors.ink },
  flagReason: { color: colors.muted },
  suggestion: { color: colors.ink, marginBottom: spacing(2), lineHeight: 20 },
});
