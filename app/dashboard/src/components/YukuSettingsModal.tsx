import {
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Select,
  Spinner,
  Tag,
  TagLabel,
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
import {
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
} from "./PageOrModal";
import { FC, useEffect, useMemo, useRef, useState } from "react";
import { fetch } from "service/http";

type YukuSettingsModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

// Announce template variables with the sample values used for the live preview.
// Kept in sync with ANNOUNCE_VARIABLES / setup_format_variables on the backend.
const ANNOUNCE_VARS: Array<[string, string]> = [
  ["USERNAME", "ivan_2026"],
  ["DAYS_LEFT", "12"],
  ["TIME_LEFT", "12d 4h"],
  ["EXPIRE_DATE", "2026-08-06"],
  ["DATA_USAGE", "3.2 GB"],
  ["DATA_LIMIT", "50.0 GB"],
  ["DATA_LEFT", "46.8 GB"],
  ["GROUP_NAME", "LTE"],
  ["GROUP_USED", "12.3 GB"],
  ["GROUP_LIMIT", "100.0 GB"],
  ["GROUP_LEFT", "87.7 GB"],
  ["GROUPS", "LTE: 12.3 GB / 100.0 GB"],
  ["DEVICE_COUNT", "2"],
  ["DEVICE_LIMIT", "5"],
  ["DEVICE_LEFT", "3"],
  ["STATUS_EMOJI", "✅"],
  ["STATUS_TEXT", "Active"],
  ["SERVER_IP", "51.250.38.20"],
];

const renderPreview = (template: string): string =>
  ANNOUNCE_VARS.reduce(
    (text, [name, sample]) => text.split(`{${name}}`).join(sample),
    template
  );

type Settings = {
  expired_notice: string;
  device_limit_notice: string;
  default_device_limit: string;
  announce: string;
  announce_align: string;
  subscription_routing: string;
  auto_select_remark: string;
  auto_select_strategy: string;
  auto_select_interval: string;
  auto_select_destination: string;
  auto_select_groups: string;
};

export type AutoSelectGroup = {
  remark: string;
  strategy: string;
  interval: string;
  destination: string;
};

const EMPTY_GROUP: AutoSelectGroup = {
  remark: "",
  strategy: "leastLoad",
  interval: "1m",
  destination: "",
};

const EMPTY: Settings = {
  expired_notice: "",
  device_limit_notice: "",
  default_device_limit: "0",
  announce: "",
  announce_align: "left",
  subscription_routing: "off",
  auto_select_remark: "",
  auto_select_strategy: "leastLoad",
  auto_select_interval: "1m",
  auto_select_destination: "",
  auto_select_groups: "",
};

/** Groups as stored, falling back to the single-group keys the feature
 *  shipped with so an older panel's entry isn't silently dropped. */
const readGroups = (settings: Settings): AutoSelectGroup[] => {
  let parsed: any = [];
  if (settings.auto_select_groups) {
    try {
      parsed = JSON.parse(settings.auto_select_groups);
    } catch {
      parsed = [];
    }
  }
  const groups: AutoSelectGroup[] = (Array.isArray(parsed) ? parsed : []).map(
    (g: any) => ({ ...EMPTY_GROUP, ...(g || {}) })
  );
  if (groups.length === 0) {
    groups.push({
      remark: settings.auto_select_remark || "",
      strategy: settings.auto_select_strategy || EMPTY_GROUP.strategy,
      interval: settings.auto_select_interval || EMPTY_GROUP.interval,
      destination: settings.auto_select_destination || "",
    });
  }
  return groups;
};

// Kept in sync with AUTO_SELECT_STRATEGIES in app/subscription/v2ray.py.
const AUTO_SELECT_STRATEGIES: Array<[string, string]> = [
  ["leastLoad", "leastLoad — самый быстрый по замерам (burstObservatory)"],
  ["leastPing", "leastPing — самый низкий пинг (observatory)"],
  ["roundRobin", "roundRobin — по очереди, без замеров"],
  ["random", "random — случайный, без замеров"],
];

// Mirrors align_announce() in app/subscription/share.py: emoji/CJK count as two
// cells, variation selectors and ZWJ as none.
const displayWidth = (line: string): number => {
  let width = 0;
  const chars = Array.from(line);
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    const next = chars[i + 1] ?? "";
    if (ch === "\uFE0F" || ch === "\uFE0E" || ch === "\u200D") continue;
    if (next === "\uFE0F") {
      width += 2;
      continue;
    }
    width += (ch.codePointAt(0) ?? 0) >= 0x1f300 ? 2 : 1;
  }
  return width;
};

const alignAnnounce = (text: string, align: string): string => {
  if (align !== "center" || !text) return text;
  const lines = text.split("\n").map((l) => l.trim());
  const width = Math.max(...lines.map(displayWidth), 0);
  return lines
    .map((l) =>
      l ? " ".repeat(Math.max(Math.floor((width - displayWidth(l)) / 2), 0)) + l : l
    )
    .join("\n");
};

export const YukuSettingsModal: FC<YukuSettingsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<Settings>(EMPTY);
  const [groups, setGroups] = useState<AutoSelectGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const announceRef = useRef<HTMLTextAreaElement | null>(null);
  const toast = useToast();

  const preview = useMemo(
    () => alignAnnounce(renderPreview(data.announce), data.announce_align),
    [data.announce, data.announce_align]
  );

  // insert {VAR} where the caret is, so building a template stays one click
  const insertVariable = (name: string) => {
    const el = announceRef.current;
    const token = `{${name}}`;
    if (!el) {
      setData((d) => ({ ...d, announce: d.announce + token }));
      return;
    }
    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? start;
    const next = el.value.slice(0, start) + token + el.value.slice(end);
    setData((d) => ({ ...d, announce: next }));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(start + token.length, start + token.length);
    });
  };

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch("/yuku/settings")
      .then((d: any) => {
        const settings: Settings = { ...EMPTY, ...d };
        setData(settings);
        setGroups(readGroups(settings));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isOpen]);

  const patchGroup = (index: number, patch: Partial<AutoSelectGroup>) =>
    setGroups((list) =>
      list.map((g, i) => (i === index ? { ...g, ...patch } : g))
    );

  const save = () => {
    setSaving(true);
    // the group list is the source of truth from here on; group 1 also
    // overwrites the single-group keys so both stay in step
    const first = groups[0] ?? EMPTY_GROUP;
    const body = {
      ...data,
      auto_select_groups: JSON.stringify(groups),
      auto_select_remark: first.remark,
      auto_select_strategy: first.strategy,
      auto_select_interval: first.interval,
      auto_select_destination: first.destination,
    };
    fetch("/yuku/settings", { method: "PUT", body })
      .then((d: any) => {
        const settings: Settings = { ...EMPTY, ...d };
        setData(settings);
        setGroups(readGroups(settings));
        toast({
          title: "Настройки сохранены",
          status: "success",
          isClosable: true,
          duration: 3000,
          position: "top",
        });
        onClose();
      })
      .catch((err: any) => {
        // the backend refuses e.g. deleting a group that hosts still use —
        // showing only "Ошибка сохранения" would hide why
        toast({
          title: "Ошибка сохранения",
          description:
            err?.response?._data?.detail ?? err?.data?.detail,
          status: "error",
          isClosable: true,
          duration: 6000,
          position: "top",
        });
      })
      .finally(() => setSaving(false));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>⚙️ YUKU настройки</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {loading ? (
            <Spinner />
          ) : (
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Announce (объявление в шапке подписки)</FormLabel>
                <Textarea
                  ref={announceRef}
                  rows={6}
                  fontFamily="mono"
                  fontSize="sm"
                  value={data.announce}
                  onChange={(e) =>
                    setData({ ...data, announce: e.target.value })
                  }
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Текст над списком серверов в клиенте. Подставляются данные
                  пользователя — нажми на переменную, чтобы вставить её.
                </Text>

                <Text fontSize="xs" color="gray.500" mt={2}>
                  DATA_* — общий трафик юзера и его лимит; GROUP_* — трафик в
                  группе хостов и её лимит ({"{GROUPS}"} — список всех групп
                  юзера, по строке на группу).
                </Text>
                <HStack spacing={1} wrap="wrap" mt={2}>
                  {ANNOUNCE_VARS.map(([name]) => (
                    <Tag
                      key={name}
                      size="sm"
                      cursor="pointer"
                      variant="subtle"
                      colorScheme="primary"
                      onClick={() => insertVariable(name)}
                      _hover={{ opacity: 0.75 }}
                    >
                      <TagLabel>{`{${name}}`}</TagLabel>
                    </Tag>
                  ))}
                </HStack>

                <HStack mt={3} spacing={2}>
                  <Text fontSize="xs" color="gray.500">
                    Выравнивание:
                  </Text>
                  <Select
                    size="xs"
                    maxW="150px"
                    value={data.announce_align}
                    onChange={(e) =>
                      setData({ ...data, announce_align: e.target.value })
                    }
                  >
                    <option value="left">по левому краю</option>
                    <option value="center">по центру</option>
                  </Select>
                </HStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  По центру — строки дополняются пробелами. В клиенте шрифт
                  пропорциональный, поэтому центрирование приблизительное.
                </Text>

                <Text fontSize="xs" color="gray.500" mt={3} mb={1}>
                  Превью (с примерными значениями):
                </Text>
                <Box
                  borderWidth="1px"
                  borderColor="light-border"
                  borderRadius="md"
                  p={3}
                  fontSize="sm"
                  fontFamily={data.announce_align === "center" ? "mono" : undefined}
                  whiteSpace="pre-wrap"
                  minH="60px"
                >
                  {preview || (
                    <Text as="span" color="gray.500">
                      — пусто, будет показан текст по умолчанию —
                    </Text>
                  )}
                </Box>
              </FormControl>

              <FormControl>
                <FormLabel>Сообщение при истёкшей подписке</FormLabel>
                <Textarea
                  rows={3}
                  value={data.expired_notice}
                  onChange={(e) =>
                    setData({ ...data, expired_notice: e.target.value })
                  }
                />
                <Text fontSize="xs" color="gray.500">
                  Каждая строка — отдельный «сервер»-уведомление в клиенте.
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Сообщение при превышении лимита устройств</FormLabel>
                <Textarea
                  rows={3}
                  value={data.device_limit_notice}
                  onChange={(e) =>
                    setData({ ...data, device_limit_notice: e.target.value })
                  }
                />
              </FormControl>

              <FormControl>
                <FormLabel>Роутинг и DNS в подписке (v2ray-json)</FormLabel>
                <Select
                  value={data.subscription_routing}
                  onChange={(e) =>
                    setData({ ...data, subscription_routing: e.target.value })
                  }
                >
                  <option value="off">выключено (обычный конфиг)</option>
                  <option value="yuku_routing">
                    RU split-tunnel + блокировка рекламы
                  </option>
                </Select>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Российские сайты и локальная сеть идут мимо VPN, реклама и
                  телеметрия режутся, DNS для RU-доменов — через DoH Яндекса.
                  ⚠️ Профиль повторяется в каждом конфиге: подписка вырастает с
                  десятков КБ до нескольких МБ. Включай, только если на nginx
                  включён gzip для /sub.
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Автовыбор сервера (v2ray-json)</FormLabel>
                <Text fontSize="xs" color="gray.500" mb={3}>
                  Каждая группа — отдельная запись в подписке, куда клиент сам
                  выбирает самый быстрый сервер. Хост попадает в группу в
                  настройках хоста. Нужно минимум два хоста на группу, иначе
                  запись не добавляется. В названии работают те же переменные,
                  что и в announce.
                </Text>

                <VStack spacing={3} align="stretch">
                  {groups.map((group, index) => (
                    <Box
                      key={index}
                      borderWidth="1px"
                      borderColor="light-border"
                      borderRadius="md"
                      p={3}
                    >
                      <HStack mb={2} spacing={2}>
                        <Text fontSize="sm" fontWeight="semibold" minW="8">
                          №{index + 1}
                        </Text>
                        <Input
                          size="sm"
                          placeholder={
                            index === 0 ? "🌍 Автовыбор" : `🌍 Автовыбор ${index + 1}`
                          }
                          value={group.remark}
                          onChange={(e) =>
                            patchGroup(index, { remark: e.target.value })
                          }
                        />
                        {index === groups.length - 1 && groups.length > 1 && (
                          <Button
                            size="sm"
                            variant="ghost"
                            colorScheme="red"
                            onClick={() =>
                              setGroups((list) => list.slice(0, -1))
                            }
                          >
                            Удалить
                          </Button>
                        )}
                      </HStack>
                      <HStack spacing={2} align="flex-start">
                        <Select
                          size="sm"
                          value={group.strategy}
                          onChange={(e) =>
                            patchGroup(index, { strategy: e.target.value })
                          }
                        >
                          {AUTO_SELECT_STRATEGIES.map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </Select>
                        <Input
                          size="sm"
                          maxW="90px"
                          placeholder="1m"
                          value={group.interval}
                          onChange={(e) =>
                            patchGroup(index, { interval: e.target.value })
                          }
                        />
                      </HStack>
                      <Input
                        size="sm"
                        mt={2}
                        placeholder="http://www.gstatic.com/generate_204"
                        value={group.destination}
                        onChange={(e) =>
                          patchGroup(index, { destination: e.target.value })
                        }
                      />
                    </Box>
                  ))}
                </VStack>

                <Button
                  size="sm"
                  variant="outline"
                  w="full"
                  mt={3}
                  fontWeight="normal"
                  onClick={() => setGroups((list) => [...list, { ...EMPTY_GROUP }])}
                >
                  Добавить автовыбор
                </Button>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Удалить можно только последнюю группу, и только если в ней
                  нет хостов — иначе они пропали бы из подписки молча. Слишком
                  частые замеры (меньше 30s) гоняют лишний трафик через каждый
                  сервер.
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Лимит устройств по умолчанию (0 = ∞)</FormLabel>
                <Input
                  type="number"
                  value={data.default_device_limit}
                  onChange={(e) =>
                    setData({ ...data, default_device_limit: e.target.value })
                  }
                />
                <Text fontSize="xs" color="gray.500">
                  Применяется к новым пользователям, если лимит не задан явно.
                </Text>
              </FormControl>
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Отмена
          </Button>
          <Button colorScheme="primary" isLoading={saving} onClick={save}>
            Сохранить
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
