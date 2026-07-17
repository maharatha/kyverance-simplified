import { HomePageClient } from "@/components/home";
import { HOME_PAGE_STATES, type HomePageState } from "@/lib/home";

function isHomePageState(value: string): value is HomePageState {
  return (HOME_PAGE_STATES as string[]).includes(value);
}

type HomePageProps = {
  searchParams: Promise<{ state?: string }>;
};

export default async function HomePage({ searchParams }: HomePageProps) {
  const params = await searchParams;
  const requested = params.state;
  const initialState =
    process.env.NODE_ENV !== "production" &&
    requested &&
    isHomePageState(requested)
      ? requested
      : undefined;

  return <HomePageClient initialState={initialState} />;
}
