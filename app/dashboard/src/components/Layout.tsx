import {
  Box,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerOverlay,
  HStack,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import { fetchInbounds } from "contexts/DashboardContext";
import { FC, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Outlet, useLocation } from "react-router-dom";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { Sidebar, SidebarNav } from "./Sidebar";

/** Page title per route — the sidebar says where you are, the header what it is. */
const useRouteTitle = (): string => {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const titles: Record<string, string> = {
    "/": t("users"),
    "/hosts": t("header.hostSettings"),
    "/nodes": t("header.nodeSettings"),
    "/nodes-usage": t("header.nodesUsage"),
    "/reset-usage": t("resetAllUsage"),
    "/core": t("header.coreSettings"),
    "/yuku": "YUKU настройки",
    "/groups": "Лимиты по группам",
    "/audit": "История действий",
  };
  return titles[pathname] ?? t("users");
};

export const Layout: FC = () => {
  const title = useRouteTitle();
  const drawer = useDisclosure();

  // Every screen needs the inbound list, not just the users page: opening
  // /hosts directly used to leave it empty and the page crashed on the first
  // inbound it read.
  useEffect(() => {
    fetchInbounds();
  }, []);

  return (
    <HStack align="stretch" spacing="0" minH="100vh">
      <Sidebar />

      <Drawer
        isOpen={drawer.isOpen}
        placement="left"
        onClose={drawer.onClose}
        size="xs"
      >
        <DrawerOverlay />
        <DrawerContent>
          <DrawerBody py="4" px="2">
            <VStack align="stretch" spacing="1" h="full">
              <SidebarNav onNavigate={drawer.onClose} />
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <VStack
        flex="1"
        minW="0"
        justifyContent="space-between"
        rowGap="4"
        p={{ base: "3", md: "6" }}
      >
        <Box w="full" minW="0">
          <Header title={title} onMenuOpen={drawer.onOpen} />
          {/* wide screens (tables, JSON editors) scroll inside the column
              instead of pushing the whole page sideways on a phone */}
          <Box mt="4" w="full" overflowX="auto">
            <Outlet />
          </Box>
        </Box>
        <Footer />
      </VStack>
    </HStack>
  );
};
