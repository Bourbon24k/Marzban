import {
  Button,
  FormControl,
  FormLabel,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spinner,
  Text,
  Textarea,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { FC, useEffect, useState } from "react";
import { fetch } from "service/http";

type YukuSettingsModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

type Settings = {
  expired_notice: string;
  device_limit_notice: string;
  default_device_limit: string;
  announce: string;
};

const EMPTY: Settings = {
  expired_notice: "",
  device_limit_notice: "",
  default_device_limit: "0",
  announce: "",
};

export const YukuSettingsModal: FC<YukuSettingsModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [data, setData] = useState<Settings>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

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
                  rows={3}
                  value={data.announce}
                  onChange={(e) =>
                    setData({ ...data, announce: e.target.value })
                  }
                />
                <Text fontSize="xs" color="gray.500">
                  Текст-уведомление, которое клиент показывает над списком серверов.
                </Text>
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
