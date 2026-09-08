import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

// Set EXPO_PUBLIC_API_URL in .env to your machine's LAN IP when testing on a
// physical device — "localhost" on a phone means the phone itself.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:4000";

export const apiClient = axios.create({ baseURL: API_URL });

apiClient.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("accessToken");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export async function login(email: string, password: string) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  await AsyncStorage.setItem("accessToken", data.accessToken);
  await AsyncStorage.setItem("refreshToken", data.refreshToken);
  return data.user;
}

export async function signup(email: string, password: string, displayName: string) {
  const { data } = await apiClient.post("/auth/signup", { email, password, displayName });
  await AsyncStorage.setItem("accessToken", data.accessToken);
  await AsyncStorage.setItem("refreshToken", data.refreshToken);
  return data.user;
}

export async function saveProfile(profile: Record<string, unknown>) {
  const { data } = await apiClient.put("/profile", profile);
  return data;
}

export async function submitScan(imageUris: string[]) {
  const form = new FormData();
  imageUris.forEach((uri, i) => {
    form.append("images", { uri, name: `label_${i}.jpg`, type: "image/jpeg" } as unknown as Blob);
  });
  const { data } = await apiClient.post("/scans", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
