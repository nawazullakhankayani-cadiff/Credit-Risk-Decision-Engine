import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import PlatformSection from "@/components/PlatformSection";
import SolutionsSection from "@/components/SolutionsSection";
import CustomersSection from "@/components/CustomersSection";
import AboutSection from "@/components/AboutSection";
import ContactSection from "@/components/ContactSection";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="bg-hero-bg min-h-screen">
      <Navbar />
      <main>
        <HeroSection />
        <PlatformSection />
        <SolutionsSection />
        <CustomersSection />
        <AboutSection />
        <ContactSection />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
