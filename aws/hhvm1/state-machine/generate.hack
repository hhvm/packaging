#!/usr/bin/env hhvm
/*
 *  Copyright (c) 2017-present, Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the MIT license found in the
 *  LICENSE file in the root directory of this source tree.
 *
 */

/**
 * This script generates the Amazon States Language (a.k.a. JSON) code for the
 * state machine that builds and publishes HHVM release(s).
 *
 * The state machine has a lot of nesting, so it would be pretty hard to avoid
 * mistakes while trying to write the whole JSON by hand. There are also some
 * repeated patterns (e.g. retry policies) that are much easier to keep in sync
 * if we generate them.
 */

namespace Facebook\HHVMPackaging\GenerateStateMachine;
use namespace HH\Lib\{C, Dict, Keyset, Str, Vec};

// Note: The enums below are not meant to be complete or accurate lists of
// anything, they're just here to help avoid typos and inconsistencies in the
// rest of the code.

// Activities
enum A: string as string {
  MakeSourceTarball = 'MakeSourceTarball';
  MakeBinaryPackage = 'MakeBinaryPackage';
  PublishBinaryPackages = 'PublishBinaryPackages';
  PublishSourceTarball = 'PublishSourceTarball';
  PublishDockerImages = 'PublishDockerImages';
  BuildAndPublishMacOS = 'BuildAndPublishMacOS';
}

// State names/name parts
enum S: string as string {
  // Lambda states
  ParseInput = 'ParseInput';
  GetPlatformsForVersion = 'GetPlatformsForVersion';
  UpdateIndices = 'UpdateIndices';
  InvalidateCloudFront = 'InvalidateCloudFront';
  CheckIfReposChanged = 'CheckIfReposChanged';
  NormalizeResults = 'NormalizeResults';
  CheckForFailures = 'CheckForFailures';
  HealthCheck = 'HealthCheck';
  // Activity states' name prefixes
  PrepareTo = 'PrepareTo';
  Should = 'Should';
  // "Map" state name parts
  ForEach = 'ForEach';
  Version = 'Version';
  Platform = 'Platform';
  // "Parallel" state name part
  And = 'And';
  BuildAndPublishLinux = 'BuildAndPublishLinux';
  // Suffix for an explicit "end" state, which we need to add to all nested
  // state machines because not all state types support {"End": true}
  End = 'End';
}

// ASL state types
enum T: string as string {
  Choice = 'Choice';
  Map = 'Map';
  Parallel = 'Parallel';
  Pass = 'Pass';
  Task = 'Task';
  Wait = 'Wait';
}

// ASL state fields
enum F: string as string {
  Branches = 'Branches';
  Catch = 'Catch';
  Choices = 'Choices';
  Default = 'Default';
  End = 'End';
  InputPath = 'InputPath';
  ItemsPath = 'ItemsPath';
  Iterator = 'Iterator';
  Next = 'Next';
  OutputPath = 'OutputPath';
  Parameters = 'Parameters';
  Resource = 'Resource';
  ResultPath = 'ResultPath';
  Retry = 'Retry';
  Seconds = 'Seconds';
  TimeoutSeconds = 'TimeoutSeconds';
  Type = 'Type';
}

// Common input/output parameter names
enum P: string as string {
  BuildInput = 'buildInput';
  Results = 'results';
  Version = 'version';
  Platform = 'platform';
  Activity = 'activity';
}

newtype State = dict<F, mixed>;
newtype StateMachine = shape(
  'StartAt' => string,
  'States' => dict<string, State>,
);

abstract final class Config {
  const dict<string, string> ARN = dict[
    // Lambdas
    S::ParseInput =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-parse-input',
    S::GetPlatformsForVersion =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-get-platforms-for-version',
    S::UpdateIndices =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'create-s3-index-html',
    S::InvalidateCloudFront =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm-invalidate-repository-metadata-on-cloudfront',
    S::CheckIfReposChanged =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-check-if-repos-changed',
    S::NormalizeResults =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-normalize-results',
    S::CheckForFailures =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-check-for-failures',
    S::HealthCheck =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-health-check',
    S::PrepareTo =>
      'arn:aws:lambda:us-west-2:223121549624:function:'.
      'hhvm1-prepare-activity',

    // Activities
    A::MakeSourceTarball =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-make-source-tarball',
    A::MakeBinaryPackage =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-make-binary-package',
    A::PublishBinaryPackages =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-publish-binary-packages',
    A::PublishSourceTarball =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-publish-source-tarball',
    A::PublishDockerImages =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-publish-docker-images',
    A::BuildAndPublishMacOS =>
      'arn:aws:states:us-west-2:223121549624:activity:'.
      'hhvm-build-and-publish-macos',
  ];

  const dict<A, int> TIMEOUT_SEC = dict[
    A::MakeSourceTarball => 30 * 60,
    A::MakeBinaryPackage => 180 * 60,
    A::PublishBinaryPackages => 180 * 60,
    A::PublishDockerImages => 180 * 60,
    A::PublishSourceTarball => 30 * 60,
    A::BuildAndPublishMacOS => 180 * 60,
  ];

  /**
   * These launch EC2 instances or do other API calls, which tend to
   * intermittently fail (especially when running many at once). Hence, a lot of
   * retries. Note: AWS does 2x exponential backoff by default.
   */
  const vec<dict<string, mixed>> LAMBDA_RETRY_POLICY = vec[
    dict[
      'ErrorEquals' => vec['States.ALL'],
      // retry after 5, 10, 20, 40, 80 seconds
      'IntervalSeconds' => 5,
      'MaxAttempts' => 5,
    ],
  ];

  /**
   * These do the actual building/publishing. This is expensive, and can
   * reasonably fail for legitimate reasons, so don't waste time with too
   * many retries.
   */
  const vec<dict<string, mixed>> ACTIVITY_RETRY_POLICY = vec[
    dict[
      'ErrorEquals' => vec['States.ALL'],
      // retry after 1 minute, then 5 minutes, then fail
      'IntervalSeconds' => 60,
      'MaxAttempts' => 2,
      'BackoffRate' => 5.0,
    ],
  ];
}

/**
 * Helper function to output JSON paths.
 */
function path(string ...$keys): string {
  return '$.'.Str\join($keys, '.');
}

/**
 * Returns the value to use for F::Parameters that preserves the specified
 * parameters' values...
 */
function params(P ...$keys): dict<string, string> {
  return Dict\pull($keys, $key ==> path($key), $key ==> "$key.$");
}

/**
 * ...and adds the specified parameter with the specified value.
 */
function params_with(
  keyset<P> $params_to_preserve,
  string $new_name,
  string $new_value,
): dict<string, string> {
  $params = params(...$params_to_preserve);
  $params[$new_name] = $new_value;
  return $params;
}

/**
 * ...and adds the specified parameter with value automatically produced by a
 * map state.
 */
function map_params(
  keyset<P> $params_to_preserve,
  P $map_param,
): dict<string, string> {
  return params_with($params_to_preserve, "$map_param.$", '$$.Map.Item.Value');
}

/**
 * Returns the states needed for the common pattern:
 * PrepareTo$activity  ->  Should$activity  ->  $activity  ->  $next
 *                           `-----------------------------------^
 */
function states_for_activity(
  keyset<P> $params_to_preserve,
  A $activity,
  string $next,
  string $failure_state,
): dict<string, State> {
  $params_to_preserve[] = P::BuildInput;
  return dict[
    S::PrepareTo.$activity => dict[
      F::Type => T::Task,
      F::Resource => Config::ARN[S::PrepareTo],
      F::Parameters => params_with($params_to_preserve, P::Activity, $activity),
      F::ResultPath => path(P::Results, $activity),
      F::Catch => vec[
        dict[
          'ErrorEquals' => vec['States.ALL'],
          'ResultPath' => path(P::Results, $activity, 'failure'),
          'Next' => $failure_state,
        ],
      ],
    ],
    S::Should.$activity => dict[
      F::Type => T::Choice,
      F::Choices => vec[
        dict[
          'Variable' => path(P::Results, $activity, 'skip'),
          'BooleanEquals' => true,
          'Next' => $next,
        ],
      ],
      F::Default => $activity,
    ],
    $activity => dict[
      F::Type => T::Task,
      F::Resource => Config::ARN[$activity],
      F::InputPath => path(P::Results, $activity, 'taskInput'),
      F::TimeoutSeconds => Config::TIMEOUT_SEC[$activity],
      F::Retry => Config::ACTIVITY_RETRY_POLICY,
      F::Next => $next,
    ],
  ];
}

/**
 * Automatically adds StartAt and Next/End, assuming a linear state machine with
 * states in the provided order. Also adds standard values for most fields in
 * "Task" states if missing. Existing values are never overwritten.
 */
function linear_state_machine(
  ?string $failure_state,
  dict<string, State> $states,
): StateMachine {
  $names = Vec\keys($states);
  foreach ($names as $i => $name) {
    $type = $states[$name][F::Type];

    if ($type === T::Task) {
      $states[$name][F::Resource] ??= Config::ARN[$name];
      $states[$name][F::ResultPath] ??= path(P::Results, $name, 'success');
      $states[$name][F::Retry] ??= Config::LAMBDA_RETRY_POLICY;
      if ($failure_state is nonnull) {
        $states[$name][F::Catch] ??= vec[
          dict[
            'ErrorEquals' => vec['States.ALL'],
            'ResultPath' => path(P::Results, $name, 'failure'),
            'Next' => $failure_state,
          ],
        ];
      }
    }

    if ($type === T::Map || $type === T::Parallel) {
      $states[$name][F::ResultPath] ??= path(P::Results, $name);
    }

    if (
      $type !== T::Choice &&
      !C\contains_key($states[$name], F::Next) &&
      !C\contains_key($states[$name], F::End)
    ) {
      $next = $names[$i+1] ?? null;
      if ($next is nonnull) {
        $states[$name][F::Next] = $next;
      } else {
        $states[$name][F::End] = true;
      }
    }
  }
  return shape(
    'StartAt' => C\first_keyx($states),
    'States' => $states,
  );
}

/**
 * Adds in the Succes/Failure states that we need in every nested state machine.
 */
function nested_state_machine(
  string $end_state_prefix,
  ?P $add_param_to_results,
  dict<string, State> $states,
): StateMachine {
  return linear_state_machine(
    $end_state_prefix.S::End,
    Dict\merge(
      $states,
      dict[
        $end_state_prefix.S::End => dict[
          F::Type => T::Pass,
          F::Parameters => $add_param_to_results is nonnull
            ? params($add_param_to_results, P::Results)
            : params(P::Results),
          F::End => true,
        ],
      ],
    ),
  );
}

/**
 * The two main parallel build branches.
 */
function linux_branch(): StateMachine {
  return nested_state_machine(
    S::BuildAndPublishLinux,
    null,
    Dict\merge(
      dict[
        S::GetPlatformsForVersion => dict[
          F::Type => T::Task,
          F::ResultPath => path('platforms'),
        ],
        S::ForEach.S::Platform => dict[
          F::Type => T::Map,
          F::ItemsPath => path('platforms'),
          F::Parameters =>
            map_params(keyset[P::BuildInput, P::Version], P::Platform),
          F::Iterator => nested_state_machine(
            S::Platform,
            P::Platform,
            Dict\merge(
              states_for_activity(
                keyset[P::Version, P::Platform],
                A::MakeBinaryPackage,
                S::Platform.S::End,
                S::Platform.S::End,
              ),
            ),
          ),
        ],
      ],
      states_for_activity(
        keyset[P::BuildInput, P::Version, P::Results],
        A::PublishBinaryPackages,
        A::PublishSourceTarball.S::And.A::PublishDockerImages,
        S::BuildAndPublishLinux.S::End,
      ),
      dict[
        A::PublishSourceTarball.S::And.A::PublishDockerImages => dict[
          F::Type => T::Parallel,
          F::Parameters => params(P::BuildInput, P::Version),
          F::Branches => vec[
            nested_state_machine(
              A::PublishSourceTarball,
              null,
              states_for_activity(
                keyset[P::Version],
                A::PublishSourceTarball,
                A::PublishSourceTarball.S::End,
                A::PublishSourceTarball.S::End,
              ),
            ),
            nested_state_machine(
              A::PublishDockerImages,
              null,
              states_for_activity(
                keyset[P::Version],
                A::PublishDockerImages,
                A::PublishDockerImages.S::End,
                A::PublishDockerImages.S::End,
              ),
            ),
          ],
        ],
      ],
    ),
  );
}

function macos_branch(): StateMachine {
  return nested_state_machine(
    A::BuildAndPublishMacOS,
    null,
    states_for_activity(
      keyset[P::Version],
      A::BuildAndPublishMacOS,
      A::BuildAndPublishMacOS.S::End,
      A::BuildAndPublishMacOS.S::End,
    ),
  );
}

/**
 * The complete state machine is this main branch + a small branch that does
 * periodic health checks.
 */
function main_branch(): StateMachine {
  return linear_state_machine(
    null,
    dict[
      S::ForEach.S::Version => dict[
        F::Type => T::Map,
        F::ItemsPath => path(P::BuildInput, 'versions'),
        F::Parameters => map_params(keyset[P::BuildInput], P::Version),
        F::Iterator => nested_state_machine(
          S::Version,
          P::Version,
          Dict\merge(
            states_for_activity(
              keyset[P::Version],
              A::MakeSourceTarball,
              S::BuildAndPublishLinux.S::And.A::BuildAndPublishMacOS,
              S::Version.S::End,
            ),
            dict[
              S::BuildAndPublishLinux.S::And.A::BuildAndPublishMacOS => dict[
                F::Type => T::Parallel,
                F::Parameters => params(P::BuildInput, P::Version),
                F::Branches => vec[linux_branch(), macos_branch()],
              ],
            ],
          ),
        ),
      ],

      S::CheckIfReposChanged => dict[
        F::Type => T::Task,
        F::ResultPath => path('reposChanged'),
      ],

      S::Should.S::UpdateIndices.S::And.S::InvalidateCloudFront => dict[
        F::Type => T::Choice,
        F::Choices => vec[
          dict[
            'Variable' => path('reposChanged'),
            'BooleanEquals' => false,
            'Next' => S::NormalizeResults,
          ],
        ],
        F::Default => S::UpdateIndices.S::And.S::InvalidateCloudFront,
      ],

      S::UpdateIndices.S::And.S::InvalidateCloudFront => dict[
        F::Type => T::Parallel,
        F::Parameters => params(P::BuildInput),
        F::Branches => vec[
          nested_state_machine(
            S::UpdateIndices,
            null,
            dict[
              S::UpdateIndices => dict[
                F::Type => T::Task,
                F::Parameters => dict[
                  'bucket' => 'hhvm-downloads',
                  'cloudfront' => 'E35YBTV6QCR5BA',
                ],
              ],
            ],
          ),
          nested_state_machine(
            S::InvalidateCloudFront,
            null,
            dict[
              S::InvalidateCloudFront => dict[
                F::Type => T::Task,
              ],
            ],
          ),
        ],
      ],

      S::NormalizeResults => dict[
        F::Type => T::Task,
        F::ResultPath => '$',
      ],

      S::CheckForFailures => dict[
        F::Type => T::Task,
        F::ResultPath => '$',
        // only retry on lambda service exceptions
        F::Retry => vec[
          dict[
            'ErrorEquals' => vec[
              'Lambda.ServiceException',
              'Lambda.AWSLambdaException',
              'Lambda.SdkClientException',
            ],
            'IntervalSeconds' => 5,
            'MaxAttempts' => 5,
          ],
        ],
      ],
    ],
  );
}

function generate(): StateMachine {
  return linear_state_machine(
    null,
    dict[
      S::ParseInput => dict[
        F::Type => T::Task,
        F::ResultPath => '$',
      ],

      'Root' => dict[
        F::Type => T::Parallel,
        F::OutputPath => path('results', 'Root[0]'),
        F::Branches => vec[
          main_branch(),
          linear_state_machine(
            S::HealthCheck.S::End,
            dict[
              S::HealthCheck.T::Wait => dict[
                F::Type => T::Wait,
                F::Seconds => 300,
              ],
              S::HealthCheck => dict[
                F::Type => T::Task,
                F::Parameters => dict[
                  'buildInput.$' => '$.buildInput',
                  'execution.$' => '$$.Execution.Id',
                  'endState' => S::CheckIfReposChanged,
                ],
                F::ResultPath => path('shouldRepeat'),
              ],
              S::Should.S::HealthCheck => dict[
                F::Type => T::Choice,
                F::Choices => vec[
                  dict[
                    'Variable' => path('shouldRepeat'),
                    'BooleanEquals' => true,
                    'Next' => S::HealthCheck.T::Wait,
                  ],
                ],
                F::Default => S::HealthCheck.S::End,
              ],
              S::HealthCheck.S::End => dict[
                F::Type => T::Pass,
                F::End => true,
              ],
            ],
          ),
        ],
      ],
    ],
  );
}

<<__EntryPoint>>
function main(): void {
  require_once \dirname(__FILE__).'/vendor/autoload.hack';
  \Facebook\AutoloadMap\initialize();
  echo \json_encode(generate(), \JSON_PRETTY_PRINT)."\n";
}
