import { Header } from "@/components/layout/header";
import { SearchClient } from "./search-client";

export const metadata = { title: "Firma Ara · AgencyOS" };

export default function SearchPage() {
  return (
    <div className="flex flex-col flex-1">
      <Header
        title="Firma Ara"
        description="Doğal dilde yaz: 'kadıköyde diş hekimi', 'beşiktaş psikolog', 'kaş'ta restoran'..."
      />
      <SearchClient />
    </div>
  );
}
