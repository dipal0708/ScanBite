import React, { useRef, useState } from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { submitScan } from "../api/client";
import { colors, spacing, radii } from "../theme/theme";

export default function ScanScreen({ navigation }: any) {
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [busy, setBusy] = useState(false);

  if (!permission) return <View style={styles.container} />;
  if (!permission.granted) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.helper}>LabelWise needs camera access to scan labels.</Text>
        <Pressable style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>Allow camera</Text>
        </Pressable>
      </View>
    );
  }

  async function handleCapture() {
    if (!cameraRef.current) return;
    setBusy(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
      const result = await submitScan([photo.uri]);
      navigation.navigate("Result", { scanId: result.scanId });
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
      <View style={styles.frameOverlay}>
        <View style={styles.viewfinder} />
        <Text style={styles.hint}>Fit the ingredients or nutrition panel in the box</Text>
      </View>
      <View style={styles.controls}>
        {busy ? (
          <ActivityIndicator size="large" color={colors.brand} />
        ) : (
          <Pressable style={styles.shutter} onPress={handleCapture} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.ink },
  center: { justifyContent: "center", alignItems: "center", padding: spacing(6) },
  frameOverlay: { flex: 1, justifyContent: "center", alignItems: "center" },
  viewfinder: {
    width: "80%",
    height: 220,
    borderWidth: 3,
    borderColor: colors.good,
    borderRadius: radii.md,
  },
  hint: { color: "#fff", marginTop: spacing(4), fontSize: 14 },
  controls: { position: "absolute", bottom: spacing(10), alignSelf: "center" },
  shutter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "#fff",
    borderWidth: 4,
    borderColor: colors.brand,
  },
  helper: { color: colors.paper, marginBottom: spacing(4), textAlign: "center" },
  button: { backgroundColor: colors.brand, borderRadius: radii.md, padding: spacing(4) },
  buttonText: { color: "#fff", fontWeight: "700" },
});
