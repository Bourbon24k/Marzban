import {
  Box,
  BoxProps,
  Card,
  HStack,
  SimpleGrid,
  Text,
  useColorMode,
} from "@chakra-ui/react";
import { ApexOptions } from "apexcharts";
import { FC, ReactNode } from "react";
import ReactApexChart from "react-apexcharts";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { numberWithCommas } from "utils/formatByte";

export const DeviceStatsQueryKey = "device-stats-query-key";

type PlatformCount = { platform: string; count: number };
type DeviceStatsData = {
  total_devices: number;
  active_devices: number;
  revoked_devices: number;
  users_with_limit: number;
  users_over_limit: number;
  by_platform: PlatformCount[];
};

const MiniStat: FC<{ label: string; value: ReactNode; accent?: string }> = ({
  label,
  value,
  accent,
}) => (
  <Card
    p={4}
    borderWidth="1px"
    borderColor="light-border"
    bg="#F9FAFB"
    _dark={{ borderColor: "gray.600", bg: "gray.750" }}
    boxShadow="none"
    borderRadius="12px"
  >
    <Text fontSize="xs" color="gray.500" _dark={{ color: "gray.400" }} mb={1}>
      {label}
    </Text>
    <Text fontSize="2xl" fontWeight="semibold" color={accent}>
      {value}
    </Text>
  </Card>
);

export const DeviceStats: FC<BoxProps> = (props) => {
  const { t } = useTranslation();
  const { colorMode } = useColorMode();
  const { data } = useQuery<DeviceStatsData>({
    queryKey: DeviceStatsQueryKey,
    queryFn: () => fetch("/system/devices"),
    refetchInterval: 10000,
  });

  if (!data) return null;

  const labels = data.by_platform.map((p) => p.platform);
  const series = data.by_platform.map((p) => p.count);
  const axisColor = colorMode === "dark" ? "#CBD5E0" : undefined;

  const chartOptions: ApexOptions = {
    chart: { type: "bar", toolbar: { show: false }, animations: { enabled: false } },
    plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: "60%" } },
    dataLabels: { enabled: true, style: { fontSize: "11px", colors: ["#fff"] } },
    xaxis: { categories: labels, labels: { style: { colors: axisColor } } },
    yaxis: { labels: { style: { colors: axisColor } } },
    tooltip: { theme: colorMode },
    grid: { borderColor: colorMode === "dark" ? "#2D3748" : "#E2E8F0" },
    colors: ["#805AD5"],
  };

  return (
    <Box {...props}>
      <Text fontWeight="semibold" fontSize="md" mb={3}>
        {t("deviceStats.title")}
      </Text>
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4} mb={4}>
        <MiniStat
          label={t("deviceStats.activeDevices")}
          value={numberWithCommas(data.active_devices)}
        />
        <MiniStat
          label={t("deviceStats.revoked")}
          value={numberWithCommas(data.revoked_devices)}
          accent="orange.400"
        />
        <MiniStat
          label={t("deviceStats.usersWithLimit")}
          value={numberWithCommas(data.users_with_limit)}
        />
        <MiniStat
          label={t("deviceStats.usersOverLimit")}
          value={numberWithCommas(data.users_over_limit)}
          accent={data.users_over_limit > 0 ? "red.400" : undefined}
        />
      </SimpleGrid>
      {series.length > 0 && (
        <Card
          p={4}
          borderWidth="1px"
          borderColor="light-border"
          bg="#F9FAFB"
          _dark={{ borderColor: "gray.600", bg: "gray.750" }}
          boxShadow="none"
          borderRadius="12px"
        >
          <Text fontSize="sm" color="gray.500" _dark={{ color: "gray.400" }} mb={2}>
            {t("deviceStats.byPlatform")}
          </Text>
          <ReactApexChart
            options={chartOptions}
            series={[{ name: t("deviceStats.devices"), data: series }]}
            type="bar"
            height={Math.max(140, labels.length * 38)}
          />
        </Card>
      )}
    </Box>
  );
};
