import type { MaterialType, RecognitionFieldResult } from "./api/types";

const MATERIAL_PAGE_CONFIG: Record<
  Exclude<MaterialType, "invoice">,
  {
    title: string;
    description: string;
    fields: string[];
    nextStep: string;
  }
> = {
  payment_record: {
    title: "支付记录详情",
    description: "在本页核对支付时间、金额和支付场景，避免和发票字段混在一起。",
    fields: ["amount_cents", "transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "确认支付记录金额和时间是否可信；若仍未归属到发票，请直接在本页下方勾选归属发票并提交更改。",
  },
  competition_notice: {
    title: "比赛通知详情",
    description: "在本页核对比赛通知中的时间、地点和费用类型线索。",
    fields: ["transaction_time", "location", "expense_type", "trip_route"],
    nextStep: "确认比赛名称相关时间和地点线索是否足够支持报名费或差旅材料；需要归属发票时，直接在本页下方勾选并提交。",
  },
  itinerary: {
    title: "行程单详情",
    description: "在本页核对行程路线、机场代码和舱位信息，分摊仍在发票页处理。",
    fields: [
      "transaction_time",
      "location",
      "expense_type",
      "trip_route",
      "transport_mode",
      "cabin_class",
      "departure_airport_code",
      "arrival_airport_code",
      "return_departure_airport_code",
      "return_arrival_airport_code",
    ],
    nextStep: "确认路线、机场代码和舱位是否完整，便于航空或市内交通发票通过校验；需要归票时，直接在本页下方勾选。",
  },
  order_screenshot: {
    title: "订单截图详情",
    description: "在本页核对订单截图中的金额、时间和路线线索，发票补录仍在发票页处理。",
    fields: ["amount_cents", "transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "确认订单截图是否能作为住宿、交通或其他费用的辅助凭证；若需要归属发票，请在本页下方勾选。",
  },
  other_attachment: {
    title: "其他材料详情",
    description: "在本页保留系统识别出的时间、地点和费用线索，避免填入不适用的发票字段。",
    fields: ["transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "若系统误判了材料类型，请先改正类型；否则只保留明确可读的辅助线索，并在本页下方处理归属发票。",
  },
};

const LOCAL_TRANSPORT_ITINERARY_FIELDS = [
  "transaction_time",
  "location",
  "expense_type",
  "trip_route",
  "transport_mode",
] as const;

const AIRFARE_ITINERARY_FIELDS = [
  "transaction_time",
  "location",
  "expense_type",
  "trip_route",
  "transport_mode",
  "cabin_class",
  "departure_airport_code",
  "arrival_airport_code",
  "return_departure_airport_code",
  "return_arrival_airport_code",
] as const;

export type NonInvoiceMaterialDetailConfig = {
  title: string;
  description: string;
  fields: string[];
  nextStep: string;
};

export function resolveNonInvoiceMaterialDetailConfig(
  materialType: MaterialType,
  recognizedFields: Record<string, RecognitionFieldResult> | null | undefined,
): NonInvoiceMaterialDetailConfig | null {
  if (materialType === "invoice") {
    return null;
  }

  if (materialType !== "itinerary") {
    return MATERIAL_PAGE_CONFIG[materialType];
  }

  const expenseType = recognizedFields?.expense_type?.value
    ?? recognizedFields?.expense_type_candidate?.value
    ?? null;
  if (expenseType === "local_transport") {
    return {
      ...MATERIAL_PAGE_CONFIG.itinerary,
      description: "在本页核对市内交通行程单的时间、路线和出行方式；航空字段会自动隐藏。",
      fields: [...LOCAL_TRANSPORT_ITINERARY_FIELDS],
      nextStep: "确认上车时间、路线和出行方式是否完整；若需要归票，直接在本页下方查看或调整归属发票。",
    };
  }

  return {
    ...MATERIAL_PAGE_CONFIG.itinerary,
    fields: [...AIRFARE_ITINERARY_FIELDS],
  };
}
