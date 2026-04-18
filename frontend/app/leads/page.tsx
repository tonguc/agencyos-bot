import { Header } from "@/components/layout/header";
import { Suspense } from "react";
import { LeadsTable } from "./leads-table";

export default function LeadsPage() {
  return (
    <div className="flex flex-col flex-1">
      <Header title="Adaylar" description="Sektöre göre gruplu müşteri adayları" />
      <Suspense>
        <LeadsTable />
      </Suspense>
    </div>
  );
}
