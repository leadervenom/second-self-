"use client";

import MascotFace from "@/components/mascot/MascotFace";
import Button from "@/components/ui/Button";
import ArrowIcon from "@/components/ui/ArrowIcon";

interface CompleteScreenProps {
  name: string;
  onBack?: () => void;
}

export default function CompleteScreen({ name, onBack }: CompleteScreenProps) {
  const handleOpenAssistant = () => {
    localStorage.setItem("secondSelfName", name || "Vajhra");
    window.location.href = "/chat";
  };

  return (
    <div className="relative flex flex-col items-center gap-6 w-full max-w-[615px] px-4">
      {onBack && (
        <button
          onClick={onBack}
          className="absolute top-0 left-4 flex items-center gap-1 text-sm text-black/40 hover:text-black/60 transition-colors"
        >
          <ArrowIcon className="w-4 h-4 rotate-180" />
          back
        </button>
      )}

      <MascotFace className="w-28 sm:w-36" />

      <div className="flex flex-col items-center gap-3 w-full">
        <h1 className="text-3xl sm:text-4xl font-semibold text-black text-center">
          you&apos;re all set, {name || "friend"}
        </h1>
        <p className="text-base sm:text-lg text-gray-600 text-center">
          your second self is ready. open the web assistant to get started.
        </p>
      </div>

      <Button onClick={handleOpenAssistant} showArrow={true}>
        open web assistant
      </Button>
    </div>
  );
}
