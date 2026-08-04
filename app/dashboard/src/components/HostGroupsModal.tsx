import {
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  Input,
  Select,
  Spinner,
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
import { DeleteIcon } from "./DeleteUserModal";
import { FC, useEffect, useMemo, useState } from "react";
import { fetch } from "service/http";

const GB = 1024 ** 3;

type HostGroupsModalProps = { isOpen: boolean; onClose: () => void };

type HostCandidate = { id: number; remark: string; inbound_tag: string };
type NodeItem = { id: number; name: string };
type Group = {
  id: number;
  name: string;
  traffic_limit: number | null;
  reset_strategy: string;
  notice_text: string | null;
  include_master: boolean;
  host_ids: number[];
  node_ids: number[];
};

type Draft = {
  id?: number;
  name: string;
  limitGB: string;
  reset_strategy: string;
  notice_text: string;
  include_master: boolean;
  host_ids: number[];
  node_ids: number[];
};

const EMPTY_DRAFT: Draft = {
  name: "",
  limitGB: "",
  reset_strategy: "no_reset",
  notice_text: "",
  include_master: false,
  host_ids: [],
  node_ids: [],
};

export const HostGroupsModal: FC<HostGroupsModalProps> = ({ isOpen, onClose }) => {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [groups, setGroups] = useState<Group[]>([]);
  const [candidates, setCandidates] = useState<HostCandidate[]>([]);
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);

  const notify = (title: string, status: "success" | "error") =>
    toast({ title, status, isClosable: true, duration: 3000, position: "top" });

  const loadAll = () => {
    setLoading(true);
    // each request is independent so one failing endpoint can't blank the
    // others (e.g. host list staying empty because /nodes hiccuped)
    Promise.allSettled([
      fetch("/host-groups"),
      fetch("/host-candidates"),
      fetch("/nodes"),
    ])
      .then(([g, c, n]: any) => {
        if (g.status === "fulfilled") setGroups(g.value || []);
        if (c.status === "fulfilled") setCandidates(c.value || []);
        if (n.status === "fulfilled")
          setNodes((n.value || []).map((x: any) => ({ id: x.id, name: x.name })));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) {
      setDraft(null);
      loadAll();
    }
  }, [isOpen]);

  // node_id -> group name, for "node already used by another group" warnings
  const nodeOwner = useMemo(() => {
    const m: Record<number, string> = {};
    groups.forEach((g) => {
      if (draft && g.id === draft.id) return;
      g.node_ids.forEach((nid) => (m[nid] = g.name));
    });
    return m;
  }, [groups, draft]);

  const hostsByInbound = useMemo(() => {
    const m: Record<string, HostCandidate[]> = {};
    candidates.forEach((h) => {
      (m[h.inbound_tag] = m[h.inbound_tag] || []).push(h);
    });
    return m;
  }, [candidates]);

  const startNew = () => setDraft({ ...EMPTY_DRAFT });
  const startEdit = (g: Group) =>
    setDraft({
      id: g.id,
      name: g.name,
      limitGB: g.traffic_limit ? String(Math.round((g.traffic_limit / GB) * 100) / 100) : "",
      reset_strategy: g.reset_strategy || "no_reset",
      notice_text: g.notice_text || "",
      include_master: !!g.include_master,
      host_ids: [...g.host_ids],
      node_ids: [...g.node_ids],
    });

  const toggle = (key: "host_ids" | "node_ids", id: number) => {
    if (!draft) return;
    const has = draft[key].includes(id);
    setDraft({
      ...draft,
      [key]: has ? draft[key].filter((x) => x !== id) : [...draft[key], id],
    });
  };

  const save = () => {
    if (!draft) return;
    if (!draft.name.trim()) return notify("Укажите название", "error");
    const gb = parseFloat(draft.limitGB);
    const body = {
      name: draft.name.trim(),
      traffic_limit: draft.limitGB && !isNaN(gb) ? Math.round(gb * GB) : 0,
      reset_strategy: draft.reset_strategy,
      notice_text: draft.notice_text || null,
      include_master: draft.include_master,
      host_ids: draft.host_ids,
      node_ids: draft.node_ids,
    };
    setSaving(true);
    const req = draft.id
      ? fetch(`/host-group/${draft.id}`, { method: "PUT", body })
      : fetch("/host-group", { method: "POST", body });
    req
      .then(() => {
        notify("Группа сохранена", "success");
        setDraft(null);
        loadAll();
      })
      .catch((e: any) =>
        notify(e?.data?.detail || "Ошибка сохранения", "error")
      )
      .finally(() => setSaving(false));
  };

  const remove = (g: Group) => {
    if (!window.confirm(`Удалить группу «${g.name}»?`)) return;
    fetch(`/host-group/${g.id}`, { method: "DELETE" })
      .then(() => {
        notify("Группа удалена", "success");
        loadAll();
      })
      .catch(() => notify("Ошибка удаления", "error"));
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" isCentered scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>📊 Лимиты трафика по группам хостов</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {loading ? (
            <Spinner />
          ) : draft ? (
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Название группы</FormLabel>
                <Input
                  value={draft.name}
                  placeholder="напр. play2go"
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </FormControl>

              <HStack align="start" flexDir={{ base: "column", sm: "row" }} spacing={{ base: 0, sm: 2 }} gap={{ base: 3, sm: 0 }}>
                <FormControl>
                  <FormLabel>Лимит на юзера (ГБ)</FormLabel>
                  <Input
                    type="number"
                    value={draft.limitGB}
                    placeholder="0 = безлимит"
                    onChange={(e) => setDraft({ ...draft, limitGB: e.target.value })}
                  />
                </FormControl>
                <FormControl>
                  <FormLabel>Сброс</FormLabel>
                  <Select
                    value={draft.reset_strategy}
                    onChange={(e) =>
                      setDraft({ ...draft, reset_strategy: e.target.value })
                    }
                  >
                    <option value="no_reset">Без сброса</option>
                    <option value="day">Ежедневно</option>
                    <option value="week">Еженедельно</option>
                    <option value="month">Ежемесячно</option>
                    <option value="year">Ежегодно</option>
                  </Select>
                </FormControl>
              </HStack>

              <FormControl>
                <FormLabel>Текст-заглушка при превышении</FormLabel>
                <Textarea
                  rows={2}
                  value={draft.notice_text}
                  placeholder="🔴 Лимит трафика группы исчерпан"
                  onChange={(e) =>
                    setDraft({ ...draft, notice_text: e.target.value })
                  }
                />
              </FormControl>

              <FormControl>
                <FormLabel>Ноды для учёта трафика</FormLabel>
                <Checkbox
                  mb={2}
                  isChecked={draft.include_master}
                  onChange={() =>
                    setDraft({ ...draft, include_master: !draft.include_master })
                  }
                >
                  <Text fontSize="sm">Мастер-нода (сама панель)</Text>
                </Checkbox>
                <VStack align="stretch" spacing={1} maxH="160px" overflowY="auto"
                        borderWidth="1px" borderRadius="md" p={2}>
                  {nodes.map((n) => {
                    const owner = nodeOwner[n.id];
                    return (
                      <Checkbox
                        key={n.id}
                        isChecked={draft.node_ids.includes(n.id)}
                        onChange={() => toggle("node_ids", n.id)}
                      >
                        <HStack spacing={2}>
                          <Text fontSize="sm">{n.name}</Text>
                          {owner && (
                            <Badge colorScheme="orange" fontSize="9px">
                              уже в «{owner}»
                            </Badge>
                          )}
                        </HStack>
                      </Checkbox>
                    );
                  })}
                  {nodes.length === 0 && (
                    <Text fontSize="xs" color="gray.500">Нет нод</Text>
                  )}
                </VStack>
                <Text fontSize="xs" color="gray.500">
                  Учёт трафика идёт по нодам. Нода должна быть только в одной группе.
                </Text>
              </FormControl>

              <FormControl>
                <FormLabel>Хосты группы (показ/энфорс)</FormLabel>
                <VStack align="stretch" spacing={2} maxH="200px" overflowY="auto"
                        borderWidth="1px" borderRadius="md" p={2}>
                  {Object.entries(hostsByInbound).map(([tag, hs]) => (
                    <Box key={tag}>
                      <Text fontSize="11px" color="gray.500" mb={1}>{tag}</Text>
                      {hs.map((h) => (
                        <Checkbox
                          key={h.id}
                          ml={2}
                          isChecked={draft.host_ids.includes(h.id)}
                          onChange={() => toggle("host_ids", h.id)}
                        >
                          <Text fontSize="sm">{h.remark}</Text>
                        </Checkbox>
                      ))}
                    </Box>
                  ))}
                  {candidates.length === 0 && (
                    <Text fontSize="xs" color="gray.500">Нет хостов</Text>
                  )}
                </VStack>
              </FormControl>
            </VStack>
          ) : (
            <VStack spacing={2} align="stretch">
              {groups.length === 0 && (
                <Text fontSize="sm" color="gray.500">
                  Групп пока нет. Создайте первую — на текущих юзеров это не влияет.
                </Text>
              )}
              {groups.map((g) => (
                <HStack
                  key={g.id}
                  justify="space-between"
                  borderWidth="1px"
                  borderRadius="md"
                  p={3}
                  flexWrap="wrap"
                  gap={2}
                >
                  <Box minW="0">
                    <Text fontWeight="600">{g.name}</Text>
                    <Text fontSize="xs" color="gray.500">
                      {g.traffic_limit
                        ? `${Math.round((g.traffic_limit / GB) * 100) / 100} ГБ/юзер`
                        : "безлимит"}{" "}
                      · {g.node_ids.length} нод · {g.host_ids.length} хостов
                      {g.reset_strategy !== "no_reset" ? ` · сброс: ${g.reset_strategy}` : ""}
                    </Text>
                  </Box>
                  <HStack>
                    <Button size="xs" onClick={() => startEdit(g)}>
                      Изменить
                    </Button>
                    <IconButton
                      aria-label="delete"
                      size="xs"
                      variant="ghost"
                      colorScheme="red"
                      icon={<DeleteIcon />}
                      onClick={() => remove(g)}
                    />
                  </HStack>
                </HStack>
              ))}
              <Divider my={2} />
              <Button size="sm" onClick={startNew}>
                + Новая группа
              </Button>
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          {draft ? (
            <HStack>
              <Button variant="ghost" onClick={() => setDraft(null)}>
                Назад
              </Button>
              <Button colorScheme="primary" isLoading={saving} onClick={save}>
                Сохранить
              </Button>
            </HStack>
          ) : (
            <Button variant="ghost" onClick={onClose}>
              Закрыть
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};
