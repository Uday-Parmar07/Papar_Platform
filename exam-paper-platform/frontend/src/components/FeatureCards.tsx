import { TrendingUp, BarChart, Download } from './icons'

interface FeatureCard {
  icon: React.ReactNode
  title: string
  description: string
  gradient: string
  iconBg: string
}

export default function FeatureCards() {
  const features: FeatureCard[] = [
    {
      icon: <TrendingUp className="w-5 h-5" />,
      title: 'Trend Analysis',
      description: 'AI analyzes past years to identify important topics and question patterns',
      gradient: 'from-blue-50 to-indigo-50',
      iconBg: 'bg-blue-500',
    },
    {
      icon: <BarChart className="w-5 h-5" />,
      title: 'Difficulty Bloom',
      description: 'Smart distribution across easy, medium, and hard difficulty levels',
      gradient: 'from-emerald-50 to-teal-50',
      iconBg: 'bg-emerald-500',
    },
    {
      icon: <Download className="w-5 h-5" />,
      title: 'PDF Export',
      description: 'Download your generated paper as a beautifully formatted PDF document',
      gradient: 'from-purple-50 to-pink-50',
      iconBg: 'bg-purple-500',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
      {features.map((feature, index) => (
        <div
          key={index}
          className={`relative p-6 rounded-2xl bg-gradient-to-br ${feature.gradient} border border-gray-200 hover:border-gray-300 transition-all duration-300 hover:shadow-md group cursor-pointer overflow-hidden`}
        >
          {/* Background Pattern */}
          <div className="absolute top-0 right-0 w-24 h-24 opacity-10">
            <div className="w-full h-full bg-current rounded-full -translate-x-8 -translate-y-8" />
          </div>

          <div className="relative">
            {/* Icon */}
            <div
              className={`w-12 h-12 ${feature.iconBg} rounded-xl flex items-center justify-center text-white shadow-lg group-hover:scale-110 transition-transform duration-300`}
            >
              {feature.icon}
            </div>

            {/* Content */}
            <h3 className="font-semibold text-gray-900 mt-4">{feature.title}</h3>
            <p className="text-sm text-gray-600 mt-2 leading-relaxed">
              {feature.description}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
