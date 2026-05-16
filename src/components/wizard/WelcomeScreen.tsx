"use client";

import { useEffect } from "react";
import { GoogleAuthProvider, signInWithPopup, signInWithRedirect, getRedirectResult } from "firebase/auth";
import { auth, firebaseEnabled } from "@/lib/firebase";
import { useFirebaseUser } from "@/hooks/useFirebaseUser";
import MascotFullBody from "@/components/mascot/MascotFullBody";
import Button from "@/components/ui/Button";

const provider = new GoogleAuthProvider();
provider.addScope("https://www.googleapis.com/auth/gmail.readonly");
provider.addScope("https://www.googleapis.com/auth/gmail.send");
provider.addScope("https://www.googleapis.com/auth/calendar.readonly");
provider.addScope("https://www.googleapis.com/auth/calendar.events");
provider.addScope("https://www.googleapis.com/auth/documents");
provider.addScope("https://www.googleapis.com/auth/presentations");
provider.addScope("https://www.googleapis.com/auth/drive.file");

interface WelcomeScreenProps {
  onNext: () => void;
  onSession: (sessionId: string, email: string) => void;
}

export default function WelcomeScreen({ onNext, onSession }: WelcomeScreenProps) {
  const { isLoading } = useFirebaseUser();

  const handleSkipAuth = () => {
    const demoSessionId = `demo-${crypto.randomUUID()}`;
    onSession(demoSessionId, "");
    onNext();
  };

  useEffect(() => {
    if (!firebaseEnabled || !auth) return;

    getRedirectResult(auth)
      .then((result) => {
        if (result) {
          onSession("firebase", result.user.email ?? "");
          onNext();
        }
      })
      .catch((err) => {
        console.error("Firebase redirect error:", err);
      });
  }, [onSession, onNext]);

  const handleClick = async () => {
    if (!firebaseEnabled || !auth) {
      handleSkipAuth();
      return;
    }

    try {
      const result = await signInWithPopup(auth, provider);
      const email = result.user.email ?? "";
      onSession("firebase", email);
      onNext();
    } catch (err: unknown) {
      const firebaseErr = err as { code?: string };
      if (firebaseErr.code === "auth/popup-closed-by-user") return;

      if (firebaseErr.code === "auth/popup-blocked") {
        await signInWithRedirect(auth, provider);
        return;
      }

      console.error("Firebase sign-in error:", err);
    }
  };

  return (
    <div className="flex flex-col items-center gap-3 w-full max-w-[615px] px-4">
      <MascotFullBody className="w-36 sm:w-44 md:w-52" />

      <div className="flex flex-col items-center gap-7 w-full">
        <div className="flex flex-col items-center w-full">
          <h1 className="text-3xl sm:text-4xl lg:text-[clamp(2rem,5vw,56px)] lg:leading-[64px] font-normal text-black text-center whitespace-nowrap">
            meet your{" "}
            <span className="font-semibold text-primary">second self</span>
          </h1>
          <p className="text-base sm:text-lg lg:text-2xl font-normal text-black text-center mt-1">
            an AI that lives in your notch, thinks like you, and handles tasks
            while you live your life.
          </p>
        </div>

        <div className="flex flex-col items-center gap-3 w-full">
          <Button onClick={handleClick} disabled={firebaseEnabled && isLoading}>
            {firebaseEnabled && isLoading
              ? "signing in..."
              : firebaseEnabled
              ? "let's build you"
              : "continue in demo mode"}
          </Button>

          <button
            onClick={handleSkipAuth}
            className="text-sm text-black/40 hover:text-black/60 transition-colors underline underline-offset-2"
          >
            try without sign-in
          </button>
        </div>
      </div>
    </div>
  );
}
