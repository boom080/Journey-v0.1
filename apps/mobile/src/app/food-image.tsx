import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type {
  FoodImageAnalysisResponse,
  FoodImageScaleReferenceType,
  MealType,
} from '@journey/contracts';
import { journeyRadii, journeySpacing, journeyTypography } from '@journey/design-tokens';

import { Button, Card, Chip, Field, Notice, SectionTitle } from '@/components/ui';
import { isFoodImageAnalysisEnabled } from '@/config/environment';
import {
  analyzeFoodImage,
  ApiError,
  ApiNetworkError,
  getAgentDataRevision,
  subscribeToAgentDataDeleted,
} from '@/lib/api';
import { mealLabels } from '@/lib/format';
import { useSync } from '@/providers/sync-provider';
import { useJourneyTheme } from '@/theme/theme-provider';

const meals: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack', 'other'];
const scaleReferences: { type: FoodImageScaleReferenceType; label: string }[] = [
  { type: 'none', label: '无参照' },
  { type: 'journey_card', label: 'Journey 参照卡' },
  { type: 'plate_diameter', label: '已知餐盘直径' },
  { type: 'bowl_diameter', label: '已知碗口直径' },
];
const MAX_BASE64_LENGTH = 7_000_000;

type SelectedImage = {
  uri: string;
  base64: string;
  mediaType: 'image/jpeg' | 'image/png' | 'image/webp';
  width: number;
  height: number;
};

const pickerOptions: ImagePicker.ImagePickerOptions = {
  mediaTypes: ['images'],
  allowsEditing: true,
  aspect: [4, 3],
  quality: 0.65,
  base64: true,
  exif: false,
};

function detectedMediaType(
  imageBase64: string,
  assetMediaType?: string | null,
): SelectedImage['mediaType'] {
  if (imageBase64.startsWith('/9j/')) return 'image/jpeg';
  if (imageBase64.startsWith('iVBORw0KGgo')) return 'image/png';
  if (imageBase64.startsWith('UklGR')) return 'image/webp';
  if (assetMediaType === 'image/png' || assetMediaType === 'image/webp') return assetMediaType;
  return 'image/jpeg';
}

function candidateParams(result: FoodImageAnalysisResponse) {
  const candidate = result.candidate;
  if (!candidate) return { kind: 'food' as const };
  return {
    kind: 'food' as const,
    candidateId: candidate.candidate_id,
    confirmationToken: candidate.confirmation_token,
    candidateSource: 'image',
    name: candidate.payload.name,
    energy: String(candidate.payload.energy_kcal),
    meal: candidate.payload.meal_type,
    portion: candidate.payload.portion_amount == null ? '' : String(candidate.payload.portion_amount),
    portionUnit: candidate.payload.portion_unit ?? '',
    detail: candidate.payload.detail ?? '',
    timestamp: candidate.payload.recorded_at,
  };
}

export default function FoodImageScreen() {
  const theme = useJourneyTheme();
  const sync = useSync();
  const [image, setImage] = useState<SelectedImage | null>(null);
  const [meal, setMeal] = useState<MealType>('other');
  const [note, setNote] = useState('');
  const [scaleReference, setScaleReference] =
    useState<FoodImageScaleReferenceType>('none');
  const [scaleReferenceSize, setScaleReferenceSize] = useState('');
  const [result, setResult] = useState<FoodImageAnalysisResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const featureEnabled = isFoodImageAnalysisEnabled();
  const deletionRevision = useRef(getAgentDataRevision());

  useEffect(() => subscribeToAgentDataDeleted(() => {
    const nextRevision = getAgentDataRevision();
    if (nextRevision <= deletionRevision.current) return;
    deletionRevision.current = nextRevision;
    // Keep the user-selected photo and manual fields. Only Agent-derived
    // analysis data is invalidated by a server-confirmed data deletion.
    setResult(null);
    setPending(false);
    setError('');
  }), []);

  function acceptPickerResult(picked: ImagePicker.ImagePickerResult) {
    if (picked.canceled) {
      setError('已取消选择，没有读取或上传图片。');
      return;
    }
    const asset = picked.assets[0];
    if (!asset?.base64) {
      setError('没有读取到压缩图片，请重新选择。');
      return;
    }
    if (asset.base64.length > MAX_BASE64_LENGTH) {
      setError('图片压缩后仍超过 5 MiB，请裁剪后重试。');
      return;
    }
    setImage({
      uri: asset.uri,
      base64: asset.base64,
      mediaType: detectedMediaType(asset.base64, asset.mimeType),
      width: asset.width,
      height: asset.height,
    });
    setResult(null);
    setError('');
  }

  async function pickFromLibrary() {
    setError('');
    try {
      acceptPickerResult(await ImagePicker.launchImageLibraryAsync(pickerOptions));
    } catch {
      setError('无法打开相册，请稍后重试或使用手动记录。');
    }
  }

  async function takePhoto() {
    setError('');
    try {
      const permission = await ImagePicker.requestCameraPermissionsAsync();
      if (!permission.granted) {
        setError('未获得相机权限。你仍可以从相册选择，或使用手动饮食记录。');
        return;
      }
      acceptPickerResult(await ImagePicker.launchCameraAsync(pickerOptions));
    } catch {
      setError('无法打开相机，请稍后重试或使用手动记录。');
    }
  }

  async function analyze() {
    if (!image) return;
    if (!sync.isOnline) {
      setError('离线时不能上传图片；可以继续使用手动饮食记录。');
      return;
    }
    const referenceNeedsDiameter =
      scaleReference === 'plate_diameter' || scaleReference === 'bowl_diameter';
    const referenceSize = referenceNeedsDiameter ? Number(scaleReferenceSize) : null;
    if (
      referenceNeedsDiameter
      && (!Number.isFinite(referenceSize) || referenceSize == null || referenceSize < 8 || referenceSize > 60)
    ) {
      setError('请输入 8—60 厘米之间的真实直径；不确定时请选择“无参照”。');
      return;
    }
    const requestRevision = getAgentDataRevision();
    setPending(true);
    setError('');
    setResult(null);
    try {
      const analysis = await analyzeFoodImage({
        image_base64: image.base64,
        media_type: image.mediaType,
        width: image.width,
        height: image.height,
        meal_type_hint: meal,
        note: note.trim() || null,
        scale_reference_type: scaleReference,
        scale_reference_size_cm: referenceSize,
        confirm_upload: true,
      });
      if (requestRevision !== getAgentDataRevision()) return;
      setResult(analysis);
    } catch (reason) {
      if (requestRevision !== getAgentDataRevision()) return;
      setError(
        reason instanceof ApiError || reason instanceof ApiNetworkError
          ? `${reason.message}；请使用手动饮食记录。`
          : '图片分析失败，请使用手动饮食记录。',
      );
    } finally {
      if (requestRevision === getAgentDataRevision()) setPending(false);
    }
  }

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { borderBottomColor: theme.colors.border }]}>
        <Button variant="ghost" onPress={() => router.back()}>返回</Button>
        <Text style={[styles.headerTitle, { color: theme.colors.text }]}>图片辅助估算（实验）</Text>
        <View style={styles.headerSpacer} />
      </View>
      <ScrollView contentContainerStyle={styles.content}>
        {!featureEnabled && <Notice tone="warning">图片估算当前已关闭；文字 Agent、手动饮食记录和 Journey 不受影响。</Notice>}
        {!featureEnabled && <Button onPress={() => router.replace('/record/food')}>使用手动饮食记录</Button>}
        {featureEnabled && <>
        <Notice tone="warning">实验功能：模型不能通过照片准确称重。只选择食物区域，不要上传人脸、未成年人、证件或病历；照片不会保存，结果必须由你校正。</Notice>
        {!sync.isOnline && <Notice tone="warning">当前离线：图片分析不可用，手动饮食记录仍可使用。</Notice>}

        <Card>
          <SectionTitle>1. 选择一张食物照片</SectionTitle>
          <Notice>
            尽量俯拍，让食物和完整盘沿、碗口或 Journey 参照卡同时入镜；参照不完整时模型会忽略它。
          </Notice>
          <View style={styles.actions}>
            <View style={styles.action}><Button variant="secondary" onPress={() => void takePhoto()}>拍照</Button></View>
            <View style={styles.action}><Button variant="secondary" onPress={() => void pickFromLibrary()}>从相册选择</Button></View>
          </View>
          {image ? (
            <Image accessibilityLabel="待分析食物照片" source={{ uri: image.uri }} contentFit="cover" style={styles.preview} />
          ) : (
            <View style={[styles.placeholder, { backgroundColor: theme.colors.hero }]}>
              <Text style={{ color: theme.colors.textMuted }}>尚未选择图片</Text>
            </View>
          )}
          <Text style={[styles.caption, { color: theme.colors.textMuted }]}>仅在你点击“同意上传并生成候选”后发送；不读取 EXIF，不保存原图。</Text>
        </Card>

        <Card>
          <SectionTitle>2. 补充信息</SectionTitle>
          <Text style={[styles.label, { color: theme.colors.text }]}>餐别</Text>
          <View style={styles.chips}>{meals.map((item) => <Chip key={item} label={mealLabels[item]} selected={meal === item} onPress={() => setMeal(item)} />)}</View>
          <Text style={[styles.label, { color: theme.colors.text }]}>尺度参照（可选）</Text>
          <View style={styles.chips}>{scaleReferences.map((item) => (
            <Chip
              key={item.type}
              label={item.label}
              selected={scaleReference === item.type}
              onPress={() => {
                setScaleReference(item.type);
                if (item.type === 'none' || item.type === 'journey_card') {
                  setScaleReferenceSize('');
                }
                setResult(null);
                setError('');
              }}
            />
          ))}</View>
          {scaleReference === 'journey_card' && (
            <Notice>
              使用按 100% 比例打印的 Journey 9×5 cm 参照卡；不要使用银行卡或证件。
            </Notice>
          )}
          {(scaleReference === 'plate_diameter' || scaleReference === 'bowl_diameter') && (
            <Field
              label={scaleReference === 'plate_diameter' ? '餐盘外沿直径（厘米）' : '碗口直径（厘米）'}
              value={scaleReferenceSize}
              onChangeText={(value) => {
                setScaleReferenceSize(value);
                setResult(null);
              }}
              keyboardType="decimal-pad"
              placeholder="例如：24"
              hint="仅填写你实际测量或明确知道的直径，范围 8—60 cm。"
            />
          )}
          <Field label="可选说明" value={note} onChangeText={setNote} maxLength={200} placeholder="例如：鸡肉饭；Mock 会用它生成演示候选" />
          <Button loading={pending} disabled={!image || !sync.isOnline} onPress={() => void analyze()}>同意上传并生成候选</Button>
          {!!error && <Notice tone="error">{error}</Notice>}
        </Card>

        {result && (
          <Card>
            <SectionTitle>3. 核对估算</SectionTitle>
            <Notice tone={result.usage.provider === 'mock' ? 'warning' : 'info'}>{result.message}{result.usage.provider === 'mock' ? ' 当前为 Mock 演示，未真实识别图片。' : ''}</Notice>
            {result.estimate?.is_food && <>
              <Text style={[styles.resultName, { color: theme.colors.text }]}>{result.estimate.name}</Text>
              <Text style={[styles.range, { color: theme.colors.primaryStrong }]}>{result.estimate.energy_min_kcal}—{result.estimate.energy_max_kcal} kcal</Text>
              <Text style={[styles.caption, { color: theme.colors.textMuted }]}>点估计 {result.estimate.energy_kcal} kcal · 置信度 {result.estimate.confidence === 'low' ? '低' : '中'} · 不是称重值 · 必须校正</Text>
              {scaleReference !== 'none' && (
                <Text style={[styles.caption, { color: theme.colors.textMuted }]}>
                  尺度参照：{result.estimate.scale_reference_used ? '模型声明已使用' : '未可靠使用'}
                </Text>
              )}
              {result.estimate.items.map((item, index) => <Text key={`${item.name}-${index}`} style={[styles.item, { color: theme.colors.text }]}>• {item.name} · {item.portion_amount ?? '?'} {item.portion_unit ?? ''} · {item.energy_kcal ?? '?'} kcal</Text>)}
              {result.estimate.assumptions.map((item) => <Text key={item} style={[styles.caption, { color: theme.colors.textMuted }]}>假设：{item}</Text>)}
            </>}
            {result.candidate ? <Button onPress={() => { setImage(null); router.push({ pathname: '/record/[kind]', params: candidateParams(result) }); }}>打开表单校正</Button> : <Button onPress={() => router.replace('/record/food')}>改用手动饮食记录</Button>}
            <Text style={[styles.caption, { color: theme.colors.textMuted }]}>图片保留：否 · {result.usage.provider}/{result.usage.model} · {result.usage.latency_ms} ms · ${result.usage.estimated_cost_usd.toFixed(6)}</Text>
          </Card>
        )}

        <Button variant="ghost" onPress={() => router.push('/record/food')}>直接手动记录饮食</Button>
        </>}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  header: { minHeight: 58, borderBottomWidth: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: journeySpacing.md },
  headerTitle: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  headerSpacer: { width: 72 },
  content: { width: '100%', maxWidth: 620, alignSelf: 'center', padding: journeySpacing.lg, gap: journeySpacing.md },
  actions: { flexDirection: 'row', gap: journeySpacing.sm },
  action: { flex: 1 },
  preview: { width: '100%', aspectRatio: 4 / 3, borderRadius: journeyRadii.md },
  placeholder: { width: '100%', aspectRatio: 4 / 3, borderRadius: journeyRadii.md, alignItems: 'center', justifyContent: 'center' },
  caption: { fontSize: journeyTypography.caption, lineHeight: 18 },
  label: { fontSize: journeyTypography.small, fontWeight: '700' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: journeySpacing.sm },
  resultName: { fontSize: journeyTypography.subtitle, fontWeight: '800' },
  range: { fontSize: 26, fontWeight: '900' },
  item: { fontSize: journeyTypography.small, lineHeight: 21 },
});
