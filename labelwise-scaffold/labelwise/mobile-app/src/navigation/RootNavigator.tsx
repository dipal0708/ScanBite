import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import LoginScreen from "../screens/LoginScreen";
import OnboardingScreen from "../screens/OnboardingScreen";
import ScanScreen from "../screens/ScanScreen";
import ResultScreen from "../screens/ResultScreen";
import ProfileScreen from "../screens/ProfileScreen";

export type RootStackParamList = {
  Login: undefined;
  Onboarding: undefined;
  Scan: undefined;
  Result: { scanId: string };
  Profile: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }} initialRouteName="Login">
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        <Stack.Screen name="Scan" component={ScanScreen} />
        <Stack.Screen name="Result" component={ResultScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
