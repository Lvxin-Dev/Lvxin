import React, { useState } from 'react';
import { Check, Info } from 'lucide-react';

function App() {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'annual'>('monthly');

  const stats = [
    { value: '34,710,665', label: 'CONVERSIONS' },
    { value: '1,279,663', label: 'VOICES TRAINED' },
    { value: '6,156,902', label: 'KITS CREATORS' }
  ];

  const plans = [
    {
      name: 'Convertor',
      price: billingPeriod === 'monthly' ? 7.99 : 95.88,
      originalPrice: billingPeriod === 'monthly' ? 9.99 : 119.88,
      yearlyPrice: '$96 billed yearly',
      color: 'from-purple-400 via-purple-500 to-pink-500',
      buttonColor: 'bg-gradient-to-r from-purple-500 via-purple-600 to-pink-500 shadow-lg shadow-purple-500/25',
      cardGlow: 'shadow-purple-500/10',
      badge: null,
      features: {
        voiceSlots: 2,
        downloadMinutes: '30/mo',
        conversions: 'Unlimited'
      },
      featureList: [
        'Custom voice cloning and blended voices',
        'Premium download quality (.wav)',
        'AI vocal toolkit (vocal remover, de-harmony, de-echo, de-reverb)',
        'AI mixing and mastering',
        '75+ royalty free singing voices',
        '25+ instruments'
      ]
    },
    {
      name: 'Creator',
      price: billingPeriod === 'monthly' ? 19.99 : 239.88,
      originalPrice: billingPeriod === 'monthly' ? 24.99 : 299.88,
      yearlyPrice: '$240 billed yearly',
      color: 'from-emerald-400 via-teal-500 to-cyan-500',
      buttonColor: 'bg-gradient-to-r from-emerald-500 via-teal-600 to-cyan-500 shadow-lg shadow-teal-500/25',
      cardGlow: 'shadow-teal-500/15',
      badge: 'RECOMMENDED',
      features: {
        voiceSlots: 5,
        downloadMinutes: '75/mo',
        conversions: 'Unlimited'
      },
      featureList: [
        'Custom voice cloning and blended voices',
        'Premium download quality (.wav)',
        'AI vocal toolkit (vocal remover, de-harmony, de-echo, de-reverb)',
        'AI mixing and mastering',
        '75+ royalty free singing voices',
        '25+ instruments'
      ]
    },
    {
      name: 'Composer',
      price: billingPeriod === 'monthly' ? 47.99 : 575.88,
      originalPrice: billingPeriod === 'monthly' ? 59.99 : 719.88,
      yearlyPrice: '$576 billed yearly',
      color: 'from-green-400 via-emerald-500 to-green-600',
      buttonColor: 'bg-gradient-to-r from-green-500 via-emerald-600 to-green-700 shadow-lg shadow-green-500/25',
      cardGlow: 'shadow-green-500/10',
      badge: null,
      features: {
        voiceSlots: 12,
        downloadMinutes: 'Unlimited',
        conversions: 'Unlimited',
        beta: true
      },
      featureList: [
        'Custom voice cloning and blended voices',
        'Premium download quality (.wav)',
        'AI vocal toolkit (vocal remover, de-harmony, de-echo, de-reverb)',
        'AI mixing and mastering',
        '75+ royalty free singing voices',
        '25+ instruments'
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 via-gray-900 to-black relative overflow-hidden">
      {/* Subtle overlay for depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/20 to-black/60 pointer-events-none"></div>
      
      {/* Ambient glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-600/5 rounded-full blur-3xl"></div>
      <div className="absolute top-1/4 right-1/4 w-80 h-80 bg-teal-600/5 rounded-full blur-3xl"></div>
      
      <div className="relative z-10">
        {/* Header */}
        <div className="text-center py-16">
          <h1 className="text-5xl font-bold text-white mb-12 tracking-tight">
            Payment & pricing
          </h1>
          
          {/* Stats */}
          <div className="flex justify-center space-x-20 mb-16">
            {stats.map((stat, index) => (
              <div key={index} className="text-center group">
                <div className="text-3xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors duration-300">
                  {stat.value}
                </div>
                <div className="text-sm text-gray-400 tracking-widest font-medium">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>

          {/* Billing Toggle */}
          <div className="flex justify-center mb-16">
            <div className="bg-black/40 backdrop-blur-sm border border-gray-800/50 rounded-full p-1.5 flex shadow-2xl">
              <button
                onClick={() => setBillingPeriod('monthly')}
                className={`px-8 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
                  billingPeriod === 'monthly'
                    ? 'bg-gradient-to-r from-gray-700 to-gray-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                }`}
              >
                MONTHLY BILLING
              </button>
              <button
                onClick={() => setBillingPeriod('annual')}
                className={`px-8 py-3 rounded-full text-sm font-semibold transition-all duration-300 ${
                  billingPeriod === 'annual'
                    ? 'bg-gradient-to-r from-gray-700 to-gray-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                }`}
              >
                ANNUAL BILLING
              </button>
            </div>
          </div>

          {/* Pricing Cards */}
          <div className="max-w-7xl mx-auto px-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
              {plans.map((plan, index) => (
                <div key={index} className="relative group">
                  {plan.badge && (
                    <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 z-20">
                      <span className="bg-gradient-to-r from-teal-400 to-cyan-400 text-black px-4 py-2 rounded-full text-xs font-bold tracking-wide shadow-lg">
                        {plan.badge}
                      </span>
                    </div>
                  )}
                  
                  <div className={`bg-gradient-to-b from-gray-900/80 to-black/90 backdrop-blur-sm rounded-3xl p-8 h-full relative overflow-hidden border border-gray-800/30 shadow-2xl ${plan.cardGlow} group-hover:shadow-xl group-hover:border-gray-700/50 transition-all duration-500`}>
                    {/* Subtle inner glow */}
                    <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent rounded-3xl"></div>
                    
                    {/* Plan Header */}
                    <div className="text-center mb-8 relative z-10">
                      <h3 className="text-2xl font-bold text-white mb-6 tracking-wide">{plan.name}</h3>
                      <div className="mb-3">
                        <span className={`text-5xl font-bold bg-gradient-to-r ${plan.color} bg-clip-text text-transparent`}>
                          ${plan.price}
                        </span>
                        <span className="text-gray-500 line-through ml-3 text-lg">
                          ${plan.originalPrice} / month
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 font-medium">{plan.yearlyPrice}</div>
                    </div>

                    {/* Upgrade Button */}
                    <button className={`w-full ${plan.buttonColor} text-white font-bold py-4 rounded-2xl mb-8 hover:scale-105 hover:shadow-2xl transition-all duration-300 tracking-wide`}>
                      {plan.name === 'Convertor' ? 'GO ANNUAL' : 'UPGRADE'}
                    </button>

                    {/* Usage Stats */}
                    <div className="mb-8 relative z-10">
                      <h4 className="text-gray-400 text-sm font-bold mb-6 uppercase tracking-widest">Usage</h4>
                      <div className="space-y-4">
                        <div className="flex justify-between items-center py-2">
                          <span className="text-gray-200 font-medium">Custom voice slots</span>
                          <span className="text-white font-bold text-lg">{plan.features.voiceSlots}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                          <div className="flex items-center">
                            <span className="text-gray-200 font-medium">Download minutes</span>
                            <Info className="w-4 h-4 text-gray-500 ml-2" />
                          </div>
                          <div className="flex items-center">
                            <span className="text-white font-bold text-lg">{plan.features.downloadMinutes}</span>
                            {plan.features.beta && (
                              <span className="bg-gradient-to-r from-gray-700 to-gray-600 text-gray-300 text-xs px-3 py-1 rounded-full ml-3 font-semibold">BETA</span>
                            )}
                          </div>
                        </div>
                        <div className="flex justify-between items-center py-2">
                          <span className="text-gray-200 font-medium">Conversions</span>
                          <span className="text-white font-bold text-lg">{plan.features.conversions}</span>
                        </div>
                      </div>
                    </div>

                    {/* Features */}
                    <div className="mb-8 relative z-10">
                      <h4 className="text-gray-400 text-sm font-bold mb-6 uppercase tracking-widest">Features</h4>
                      <div className="space-y-4">
                        {plan.featureList.map((feature, featureIndex) => (
                          <div key={featureIndex} className="flex items-start">
                            <Check className="w-5 h-5 text-emerald-400 mt-0.5 mr-4 flex-shrink-0" />
                            <span className="text-gray-300 text-sm leading-relaxed">{feature}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* View All Features */}
                    <button className="w-full border border-gray-700/50 text-gray-300 py-3 rounded-xl hover:bg-gray-800/30 hover:border-gray-600/50 transition-all duration-300 font-medium tracking-wide">
                      VIEW ALL FEATURES
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Enterprise Section */}
            <div className="bg-gradient-to-r from-black/60 via-gray-900/40 to-black/60 backdrop-blur-sm rounded-3xl p-10 flex items-center justify-between border border-gray-800/30 shadow-2xl">
              <div className="flex items-center">
                <div className="bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800 p-4 rounded-2xl mr-8 shadow-lg shadow-blue-600/20">
                  <div className="w-10 h-10 bg-white/20 rounded-lg backdrop-blur-sm"></div>
                </div>
                <div>
                  <h3 className="text-3xl font-bold text-white mb-4 tracking-wide">Enterprise</h3>
                  <p className="text-gray-300 max-w-2xl leading-relaxed text-lg">
                    Enterprise plans come with direct support and customization for your specific needs. 
                    This includes personalized model training, custom voice slots, admin access to hidden 
                    and upcoming features, direct support and more.
                  </p>
                </div>
              </div>
              <div className="ml-10 flex-shrink-0">
                <button className="bg-gradient-to-r from-gray-700 via-gray-600 to-gray-700 hover:from-gray-600 hover:via-gray-500 hover:to-gray-600 text-white px-10 py-4 rounded-2xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl tracking-wide mb-6">
                  GET IN TOUCH
                </button>
                <div className="space-y-3">
                  {[
                    'Custom Number of Training Slots',
                    'Personalized Voice Training',
                    'Direct support to ensure success',
                    'Access to hidden and upcoming features'
                  ].map((feature, index) => (
                    <div key={index} className="flex items-center text-sm">
                      <Check className="w-4 h-4 text-emerald-400 mr-3" />
                      <span className="text-gray-300 font-medium">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;