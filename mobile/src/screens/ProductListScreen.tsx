import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { type CategoryNode, catalogApi, type ProductSummary } from "../api/catalog";
import { ApiError } from "../api/client";
import { formatPrice, getTexts, type Language } from "../i18n";

type Status = "loading" | "ready" | "error";

/**
 * Liste des produits de l'API en ligne (L1) avec navigation par catégorie de premier niveau
 * (A-CAT-01 : navigation par catégorie sur le mobile), pagination « Charger plus » et
 * rafraîchissement par glissement.
 */
export function ProductListScreen({ lang }: { lang: Language }) {
  const t = getTexts(lang);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [category, setCategory] = useState<string | null>(null);
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<Status>("loading");
  const [error, setError] = useState<ApiError | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const requestId = useRef(0);

  const load = useCallback(async (nextPage: number, categoryId: string | null, append: boolean) => {
    const id = ++requestId.current; // une réponse tardive ne remplace jamais une plus récente
    if (!append) setStatus("loading");
    try {
      const result = await catalogApi.products(nextPage, categoryId);
      if (id !== requestId.current) return;
      setProducts((current) => (append ? [...current, ...result.items] : result.items));
      setTotal(result.total);
      setPage(nextPage);
      setStatus("ready");
      setError(null);
    } catch (e) {
      if (id !== requestId.current) return;
      setError(e instanceof ApiError ? e : new ApiError(0, "unknown_error", String(e)));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    catalogApi.categories().then(setCategories, () => setCategories([]));
  }, []);

  useEffect(() => {
    void load(1, category, false);
  }, [category, load]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await load(1, category, false);
    setRefreshing(false);
  }, [category, load]);

  const name = (p: { name_fr: string; name_en: string }) => (lang === "en" ? p.name_en : p.name_fr);

  return (
    <View style={styles.container}>
      <Text style={styles.title} accessibilityRole="header">
        {t.title}
      </Text>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chips}>
        {[{ id: null, label: t.all }, ...categories.map((c) => ({ id: c.id, label: name(c) }))].map((chip) => (
          <Pressable
            key={chip.id ?? "all"}
            accessibilityRole="button"
            accessibilityState={{ selected: chip.id === category }}
            onPress={() => setCategory(chip.id)}
            style={[styles.chip, chip.id === category && styles.chipActive]}
          >
            <Text style={[styles.chipText, chip.id === category && styles.chipTextActive]}>{chip.label}</Text>
          </Pressable>
        ))}
      </ScrollView>

      {status === "loading" && (
        <View style={styles.center} accessibilityLiveRegion="polite">
          <ActivityIndicator size="large" color="#1d5c3a" />
          <Text style={styles.muted}>{t.loading}</Text>
        </View>
      )}

      {status === "error" && error && (
        <View style={styles.center} accessibilityRole="alert">
          <Text style={styles.error}>{error.code === "network_error" ? t.network_error : t.error}</Text>
          <Pressable accessibilityRole="button" style={styles.button} onPress={() => void load(1, category, false)}>
            <Text style={styles.buttonText}>{t.retry}</Text>
          </Pressable>
        </View>
      )}

      {status === "ready" && (
        <FlatList
          data={products}
          keyExtractor={(p) => p.id}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void refresh()} />}
          ListHeaderComponent={<Text style={styles.muted}>{t.count(total)}</Text>}
          ListEmptyComponent={<Text style={styles.muted}>{t.empty}</Text>}
          ListFooterComponent={
            products.length < total ? (
              <Pressable
                accessibilityRole="button"
                style={styles.button}
                onPress={() => void load(page + 1, category, true)}
              >
                <Text style={styles.buttonText}>{t.more}</Text>
              </Pressable>
            ) : undefined
          }
          renderItem={({ item }) => (
            <View style={styles.row} testID={`product-${item.sku}`}>
              <ProductThumb uri={item.main_image_url} />
              <View style={styles.rowBody}>
                {item.brand ? <Text style={styles.brand}>{item.brand}</Text> : null}
                <Text style={styles.name}>{name(item)}</Text>
                <Text style={styles.price}>{formatPrice(item.price_cents, lang)}</Text>
                <Text style={styles.sku}>SKU {item.sku}</Text>
              </View>
            </View>
          )}
        />
      )}
    </View>
  );
}

/** Vignette du produit; image de remplacement locale si l'image est absente ou ne se charge pas. */
export function ProductThumb({ uri }: { uri: string | null }) {
  const [failed, setFailed] = useState(false);
  if (!uri || failed) {
    return (
      <View style={[styles.image, styles.placeholder]} testID="product-placeholder" accessible={false}>
        <Text style={styles.placeholderText}>QL</Text>
      </View>
    );
  }
  return (
    <Image
      source={{ uri }}
      style={styles.image}
      onError={() => setFailed(true)}
      testID="product-image"
      accessibilityIgnoresInvertColors
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f7f6f2", paddingHorizontal: 16 },
  title: { fontSize: 24, fontWeight: "700", color: "#1f2a24", marginVertical: 12 },
  chips: { flexGrow: 0, marginBottom: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d9ddd6",
    backgroundColor: "#fff",
    marginRight: 8,
    minHeight: 40,
    justifyContent: "center",
  },
  chipActive: { backgroundColor: "#1d5c3a", borderColor: "#1d5c3a" },
  chipText: { color: "#1f2a24" },
  chipTextActive: { color: "#fff", fontWeight: "600" },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  muted: { color: "#5b6660", marginVertical: 8 },
  error: { color: "#a12a2a", textAlign: "center" },
  button: {
    backgroundColor: "#1d5c3a",
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 20,
    alignItems: "center",
    marginVertical: 12,
  },
  buttonText: { color: "#fff", fontWeight: "600" },
  row: {
    flexDirection: "row",
    backgroundColor: "#fff",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#d9ddd6",
    padding: 10,
    marginBottom: 8,
    gap: 12,
  },
  image: { width: 72, height: 72, borderRadius: 6, backgroundColor: "#e9ece6" },
  placeholder: { alignItems: "center", justifyContent: "center" },
  placeholderText: { color: "#9aa59c", fontWeight: "700", fontSize: 18 },
  rowBody: { flex: 1 },
  brand: { color: "#5b6660", fontSize: 12, textTransform: "uppercase" },
  name: { fontSize: 15, fontWeight: "600", color: "#1f2a24" },
  price: { color: "#1d5c3a", fontWeight: "700", marginTop: 2 },
  sku: { color: "#5b6660", fontSize: 12 },
});
