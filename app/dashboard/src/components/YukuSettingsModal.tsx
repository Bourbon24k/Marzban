import {
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Spinner,
  Tag,
  TagLabel,
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
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
};

const EMPTY: Settings = {
  expired_notice: "",
  device_limit_notice: "",
  default_device_limit: "0",
  announce: "",
  announce_align: "left",
};

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

// Keep in sync with ANNOUNCE_CENTER_WIDTH in app/subscription/share.py.
const ANNOUNCE_CENTER_WIDTH = 32;

const alignAnnounce = (text: string, align: string): string => {
  if (align !== "center" || !text) return text;
  const lines = text.split("\n").map((l) => l.trim());
  const width = Math.min(
    Math.max(...lines.map(displayWidth), 0),
    ANNOUNCE_CENTER_WIDTH
  );
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
      .then((d: any) => setData({ ...EMPTY, ...d }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isOpen]);

  const save = () => {
    setSaving(true);
    fetch("/yuku/settings", { method: "PUT", body: data })
      .then((d: any) => {
        setData({ ...EMPTY, ...d });
        toast({
          title: "Настройки сохранены",
          status: "success",
          isClosable: true,
          duration: 3000,
          position: "top",
        });
        onClose();
      })
      .catch(() => {
        toast({
          title: "Ошибка сохранения",
          status: "error",
          isClosable: true,
          duration: 3000,
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
