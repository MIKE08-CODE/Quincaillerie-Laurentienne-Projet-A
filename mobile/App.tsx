import { StatusBar } from "expo-status-bar";
import { Platform, StatusBar as NativeStatusBar, StyleSheet, View } from "react-native";

import { deviceLanguage } from "./src/i18n";
import { ProductListScreen } from "./src/screens/ProductListScreen";

export default function App() {
  return (
    <View style={styles.safe}>
      <StatusBar style="dark" />
      <ProductListScreen lang={deviceLanguage()} />
    </View>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: "#f7f6f2",
    paddingTop: Platform.OS === "android" ? (NativeStatusBar.currentHeight ?? 0) : 48,
  },
});
