import { Box, HStack, VStack } from "@chakra-ui/react";
import { FC } from "react";
import { useTranslation } from "react-i18next";
import { Outlet, useLocation } from "react-router-dom";
import { Footer } from "./Footer";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

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

export const Layout: FC = () => (
  <HStack align="stretch" spacing="0" minH="100vh">
    <Sidebar />
    <VStack
      flex="1"
      minW="0"
      justifyContent="space-between"
      rowGap="4"
      p="6"
    >
      <Box w="full">
        <Header title={useRouteTitle()} />
        <Box mt="4">
          <Outlet />
        </Box>
      </Box>
      <Footer />
    </VStack>
  </HStack>
);
